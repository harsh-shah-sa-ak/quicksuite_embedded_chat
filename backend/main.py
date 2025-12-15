import os
import uuid
import boto3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from botocore.exceptions import ClientError
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

app = FastAPI()

# Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



AGENT_ID = os.getenv("BEDROCK_AGENT_ID")
QS_TOPIC_ID = os.getenv("QS_TOPIC_ID")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID", "803597461034")
QUICKSIGHT_NAMESPACE = os.getenv("QUICKSIGHT_NAMESPACE", "default")
AWS_PROFILE = os.getenv("AWS_PROFILE")  # SSO profile name
AWS_USER_ARN = os.getenv("AWS_USER_ARN")
AGENT_ALIAS_ID = "CUSTOMER_ANALYTICS_AGENT"
Q_BUSINESS_APP_ID = os.getenv("Q_BUSINESS_APP_ID")
USER_ID = os.getenv("USER_ID")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")  # For temporary credentials

# Initialize QuickSight client with access key/secret key
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    print(f"🔐 Using AWS Access Key credentials")
    session_kwargs = {
        'aws_access_key_id': AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
        'region_name': AWS_REGION
    }
    # Add session token if present (for temporary credentials)
    if AWS_SESSION_TOKEN:
        session_kwargs['aws_session_token'] = AWS_SESSION_TOKEN
        print("Using temporary credentials with session token")
    session = boto3.Session(**session_kwargs)
else:
    print(f"🔐 Using AWS Profile: {AWS_PROFILE}")
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)

quicksight_client = session.client('quicksight')
qs = quicksight_client
sts_client = session.client('sts')

# Setup AWS client
bedrock_client = session.client(
    "bedrock-agent-runtime",
    region_name=os.getenv("AWS_REGION")
)

sessions = {}  # store sessionIds per user




class QARequest(BaseModel):
    query_text: str
    include_generated_answer: Optional[bool] = True
    include_q_index: Optional[bool] = True
    max_topics: Optional[int] = 4

class Query(BaseModel):
    query: str
    session_id: str | None = None

class ChatRequest(BaseModel):
    user_message: str
    conversation_id: Optional[str] = None
    parent_message_id: Optional[str] = None

class EmbedURLRequest(BaseModel):
    user_arn: str
    agent_id: Optional[str] = None
    session_lifetime_minutes: Optional[int] = 600


class EmbedURLResponse(BaseModel):
    embed_url: str
    status: int

@app.get("/api/list-agent")
def list_all_agents(max_results=100):
    resp = bedrock_client.list_agents(maxResults=max_results)
    agents = resp.get('agentSummaries', [])
    next_token = resp.get('nextToken')

    while next_token:
        resp = bedrock_client.list_agents(maxResults=max_results, nextToken=next_token)
        agents.extend(resp.get('agentSummaries', []))
        next_token = resp.get('nextToken')

    return agents

@app.post("/api/agent-chat")
async def agent_chat(request: ChatRequest):
    """
    Talks to the Unified 'Quick Suite' Agent (Amazon Q Business + QuickSight Plugin)
    """
    client = boto3.client('qbusiness', region_name=AWS_REGION)

    try:
        # Prepare arguments
        kwargs = {
            'applicationId': Q_BUSINESS_APP_ID,
            'userId': USER_ID,
            'userMessage': request.user_message,
        }
        
        # If continuing a conversation, pass these IDs
        if request.conversation_id:
            kwargs['conversationId'] = request.conversation_id
        if request.parent_message_id:
            kwargs['parentMessageId'] = request.parent_message_id

        # Call the synchronous Chat API
        response = client.chat_sync(**kwargs)

        return {
            "system_message": response.get('systemMessage'),
            "conversation_id": response.get('conversationId'),
            "parent_message_id": response.get('systemMessageId'),
            "source_attributions": response.get('sourceAttributions', []) 
            # ^ This contains links to the Dashboards or Docs used to answer
        }

    except Exception as e:
        print(f"Error calling Q Business: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask-agent")
def ask_agent(data: Query):
    # Create session for user if not exists
    session_id = data.session_id or str(uuid.uuid4())

    # Call invoke_agent
    response = bedrock_client.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        enableTrace=False,
        sessionId=session_id,
        inputText=data.query
    )

      # Bedrock Agent Runtime streams output — extract first text chunk
    chunks = []
    for event in response.get("completion", []):
        if "textResponse" in event:
            chunks.append(event["textResponse"]["body"])

    answer = "".join(chunks)

    return {
        "session_id": session_id,
        "answer": answer
    }

@app.get("/api/quicksight/list-topics")
async def list_topics():
    """
    List available QuickSight Q topics.
    This helps you understand what data sources are available for Q&A.
    """
    try:
        response = quicksight_client.list_topics(
            AwsAccountId=AWS_ACCOUNT_ID
        )
        
        topics = response.get('TopicsSummaries', [])
        
        return {
            "topics": topics,
            "count": len(topics),
            "status": 200
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=500,
            detail=f"AWS Error ({error_code}): {error_message}"
        )


@app.get("/api/quicksight/user-info")
async def get_user_info():
    """
    Get information about the current QuickSight user.
    Useful for debugging authentication issues.
    """
    try:
        # First, let's see who we are in AWS
        identity = sts_client.get_caller_identity()
        print("identity", identity);
        
        # Try to find a QuickSight user
        try:
            # Extract username from ARN if possible
            arn_parts = identity['Arn'].split('/')
            username = arn_parts[-1] if len(arn_parts) > 0 else 'unknown'
            
            # Try to describe the user
            user_response = quicksight_client.describe_user(
                UserName=username,
                AwsAccountId=AWS_ACCOUNT_ID,
                Namespace=QUICKSIGHT_NAMESPACE
            )


            print("user_response", user_response);
            
            return {
                "aws_identity": identity,
                "quicksight_user": user_response.get('User'),
                "status": "User found in QuickSight"
            }
        except ClientError as qs_error:
            return {
                "aws_identity": identity,
                "quicksight_user": None,
                "status": "AWS credentials valid, but QuickSight user not found",
                "error": str(qs_error)
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting user info: {str(e)}"
        )


@app.post("/api/quicksight/predict-qa2")
def predict_qa2(req: QARequest):
    # Assume a role that has QuickSight access
    assumed_role = sts_client.assume_role(
        RoleArn='arn:aws:iam::803597461034:role/QuickSightRole',
        RoleSessionName='QuickSightSession'
    )

    qs_session = boto3.Session(
        aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
        aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
        aws_session_token=assumed_role['Credentials']['SessionToken'],
        region_name='us-east-1'
    )

    qs = qs_session.client('quicksight')

    response = qs.predict_qa_results(
        AwsAccountId=AWS_ACCOUNT_ID,
        QueryText='what are partners to date?',
        IncludeQuickSightQIndex='INCLUDE',
        IncludeGeneratedAnswer='INCLUDE'
    )

    print("response", response);

@app.post("/api/quicksight/predict-qa")
def predict_qa(req: QARequest):
    
    # optional session id
    # if req.sessionId:
    #     payload["SessionId"] = req.sessionId

    # ---- CALL QUICK SIGHT API ----

    try:
        response = quicksight_client.predict_qa_results(
            AwsAccountId=AWS_ACCOUNT_ID,
            QueryText=req.query_text,
            IncludeQuickSightQIndex='INCLUDE',
            IncludeGeneratedAnswer='INCLUDE',
            MaxTopicsToConsider=4
        )
        
        return {
                "primary_result": response.get("PrimaryResult"),
                "additional_results": response.get("AdditionalResults", []),
                "request_id": response.get("RequestId")
            }
    except ClientError as e:
        print("e.response ++++", e.response)
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"AWS Error: {error_code} - {error_message}")

        if 'IDC user' in error_message or 'token' in error_message:
            detail={
                    "error": "QuickSight User Not Found",
                    "message": "Your SSO credentials are valid, but you need a QuickSight user provisioned.",
                    "solution": "Go to QuickSight Console → Manage QuickSight → Manage users → Invite users",
                    "aws_error": error_message
            }
            print("Detailed error", detail)
            raise HTTPException(
                status_code=403,
                detail=detail
            )
        
        if error_code == 'AccessDeniedException':
            raise HTTPException(
                status_code=403, 
                detail="Access Denied. Ensure IAM Identity Center trusted propagation is configured."
            )
        
        raise HTTPException(status_code=500, detail=error_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-embed-url/")
def get_embed_url():
    session = boto3.Session(profile_name=AWS_PROFILE)
    qs = session.client("quicksight", region_name="us-east-1")

    response = qs.generate_embed_url_for_registered_user(
        AwsAccountId=AWS_ACCOUNT_ID,
        UserArn=AWS_USER_ARN,
        ExperienceConfiguration={"QuickChat": {}},
        AllowedDomains=[
            "http://localhost:3000"  # your local React domain
        ]
    )
    
    return {"embedUrl": response["EmbedUrl"]}

@app.post("/api/quicksight/embed-url", response_model=EmbedURLResponse)
async def generate_embed_url(request: EmbedURLRequest):
    """
    Generate a secure embed URL for QuickSight Chat Agent.
    
    Args:
        request: Contains user_arn, optional agent_id, and session lifetime
        
    Returns:
        EmbedURLResponse with the generated embed URL
    """
    try:
        # Prepare experience configuration for QuickChat
        experience_configuration = {
            'QuickChat': {}
        }
        agent_id = '591980bf-7fe1-4554-be08-6c268c1a3ace'
        # If a specific agent is provided, add it to the configuration
        
        agent_arn = f"arn:aws:quicksight:{AWS_REGION}:{AWS_ACCOUNT_ID}:agent/{agent_id}"
        experience_configuration['QuickChat'] = {
            
        }
        
        # Generate embed URL
        response = quicksight_client.generate_embed_url_for_registered_user(
            AwsAccountId=AWS_ACCOUNT_ID,
            SessionLifetimeInMinutes=request.session_lifetime_minutes,
            UserArn=request.user_arn,
            ExperienceConfiguration=experience_configuration,
            AllowedDomains=['http://localhost:3000']  # Update with your domains
        )
        
        return EmbedURLResponse(
            embed_url=response['EmbedUrl'],
            status=response['Status']
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=500,
            detail=f"AWS Error ({error_code}): {error_message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating embed URL: {str(e)}"
        )


@app.post("/api/quicksight/embed-url-with-identity", response_model=EmbedURLResponse)
async def generate_embed_url_with_identity(request: EmbedURLRequest):
    """
    Generate embed URL using identity federation (no pre-provisioned QuickSight user needed).
    This is useful for dynamic user provisioning.
    """
    try:
        experience_configuration = {
            'QuickChat': {}
        }
        
        if request.agent_id:
            agent_arn = f"arn:aws:quicksight:{AWS_REGION}:{AWS_ACCOUNT_ID}:agent/{request.agent_id}"
            experience_configuration['QuickChat']['InitialAgentConfiguration'] = {
                'InitialAgentArn': agent_arn
            }
        
        response = quicksight_client.generate_embed_url_for_registered_user_with_identity(
            AwsAccountId=AWS_ACCOUNT_ID,
            SessionLifetimeInMinutes=request.session_lifetime_minutes,
            UserArn=request.user_arn,
            ExperienceConfiguration=experience_configuration,
            AllowedDomains=['http://localhost:3000']
        )
        
        return EmbedURLResponse(
            embed_url=response['EmbedUrl'],
            status=response['Status']
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise HTTPException(
            status_code=500,
            detail=f"AWS Error ({error_code}): {error_message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating embed URL: {str(e)}"
        )
