import { useEffect, useRef, useState } from 'react';
import config from './config';

export default function QuickSightEmbed() {
  const containerRef = useRef(null);
  const [embedUrl, setEmbedUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch the embed URL from your backend
    const fetchEmbedUrl = async () => {
      try {
        console.log("==>", config.API_BASE_URL);
        const response = await fetch(`${config.API_BASE_URL}/get-embed-url/`);
        if (!response.ok) {
          throw new Error('Failed to fetch embed URL');
        }
        const data = await response.json();
        setEmbedUrl(data.embedUrl);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching embed URL:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchEmbedUrl();
  }, []);

  useEffect(() => {
    if (!embedUrl || !containerRef.current) return;

    // Load the QuickSight Embedding SDK
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/amazon-quicksight-embedding-sdk@2.0.0/dist/quicksight-embedding-js-sdk.min.js';
    script.async = true;
    
    script.onload = () => {
      // SDK loaded, now embed the experience
      embedQuickSight();
    };

    document.body.appendChild(script);

    return () => {
      // Cleanup script on unmount
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, [embedUrl]);

  const embedQuickSight = async () => {
    const { createEmbeddingContext } = window.QuickSightEmbedding;

    // Create embedding context
    const embeddingContext = await createEmbeddingContext();

    // Configure the iframe container and dimensions
    const frameOptions = {
      url: embedUrl,
      container: containerRef.current,
      height: '700px',
      width: '100%',
      onChange: (changeEvent, metadata) => {
        switch (changeEvent.eventName) {
          case 'FRAME_MOUNTED': {
            console.log('QuickChat frame successfully mounted');
            break;
          }
          case 'FRAME_LOADED': {
            console.log('QuickChat experience loaded and ready');
            break;
          }
        }
      },
    };

    // Configure chat-specific options
    const contentOptions = {
      // fixedAgentArn: '<AGENT_ARN>', // Optional: specify the agent Arn to embed
      onMessage: async (messageEvent, experienceMetadata) => {
        switch (messageEvent.eventName) {
          case 'CONTENT_LOADED': {
            console.log('QuickChat interface initialized successfully');
            break;
          }
        }
      }
    };

    // Embed the QuickSight experience
    const embeddedExperience = await embeddingContext.embedQuickChat(
      frameOptions,
      contentOptions
    );

    console.log('QuickSight embedded successfully:', embeddedExperience);
  };

  if (loading) {
    return (
      <div style={{ padding: 20, textAlign: 'center' }}>
        <p>Loading QuickSight Chat...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 20, color: 'red' }}>
        <p>Error: {error}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: 20 }}>
      <h2>QuickSight Chat Agent</h2>
      <div 
        ref={containerRef} 
        id="experience-container"
        style={{ 
          border: '1px solid #ccc',
          borderRadius: '8px',
          overflow: 'hidden',
          minHeight: '700px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#f5f5f5'
        }}
      >
        {!embedUrl ? (
          <div style={{ textAlign: 'center', color: '#666' }}>
            <p>Initializing QuickSight embed...</p>
          </div>
        ) : (
          <iframe 
            src={embedUrl}
            width="100%"
            height="700px"
            title="QuickSight Chat"
          />
        )}
      </div>
    </div>
  );
}
