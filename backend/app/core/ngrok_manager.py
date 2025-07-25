"""
ngrok Manager for Development Environment

This module handles automatic ngrok tunnel creation for development environments,
allowing Cloud Tasks to access localhost services.
"""

import os
import logging
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class NgrokManager:
    """Manages ngrok tunnels for development environment."""
    
    def __init__(self):
        self._tunnel_url: Optional[str] = None
        self._is_development = os.getenv('ENVIRONMENT', '').lower() == 'development'
    
    def is_development_mode(self) -> bool:
        """Check if running in development mode."""
        return self._is_development
    
    def start_tunnel(self, port: int = 8000) -> Optional[str]:
        """
        Start ngrok tunnel for the specified port.
        
        Args:
            port: Port to tunnel (default: 8000)
            
        Returns:
            Public URL if successful, None otherwise
        """
        if not self.is_development_mode():
            logger.info("Not in development mode, skipping ngrok tunnel")
            return None
        
        try:
            # Import here to avoid dependency issues in production
            from pyngrok import ngrok
            
            # Set ngrok authtoken from environment if available
            ngrok_token = os.getenv('NGROK_AUTHTOKEN')
            if ngrok_token:
                logger.info("Setting ngrok authtoken from environment variable")
                ngrok.set_auth_token(ngrok_token)
            else:
                logger.warning("NGROK_AUTHTOKEN not found in environment. Add it to .env file or run: ngrok config add-authtoken YOUR_TOKEN")
            
            # Create tunnel
            logger.info(f"Creating ngrok tunnel for port {port}...")
            tunnel = ngrok.connect(port)
            self._tunnel_url = str(tunnel.public_url)
            
            logger.info(f"🌐 ngrok tunnel created: {self._tunnel_url}")
            
            # Update environment variables for Cloud Tasks
            os.environ['BACKEND_URL'] = self._tunnel_url
            logger.info(f"Updated BACKEND_URL to: {self._tunnel_url}")
            
            return self._tunnel_url
            
        except ImportError:
            logger.error("pyngrok not installed. Install with: pip install pyngrok")
            return None
        except Exception as e:
            logger.error(f"Failed to create ngrok tunnel: {e}")
            logger.info("Cloud Tasks will not be able to reach localhost. Consider using ngrok manually.")
            return None
    
    def stop_tunnel(self):
        """Stop ngrok tunnel and cleanup."""
        if not self.is_development_mode() or not self._tunnel_url:
            return
        
        try:
            from pyngrok import ngrok
            logger.info("Stopping ngrok tunnel...")
            ngrok.disconnect(self._tunnel_url)
            ngrok.kill()
            logger.info("ngrok tunnel stopped")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Error stopping ngrok tunnel: {e}")
        finally:
            self._tunnel_url = None
    
    @property
    def tunnel_url(self) -> Optional[str]:
        """Get the current tunnel URL."""
        return self._tunnel_url


# Global instance
_ngrok_manager = NgrokManager()


def get_ngrok_manager() -> NgrokManager:
    """Get the global ngrok manager instance."""
    return _ngrok_manager


@asynccontextmanager
async def ngrok_lifespan(app, port: int = 8000):
    """
    FastAPI lifespan context manager for ngrok tunnel.
    
    Usage in main.py:
    ```python
    from app.core.ngrok_manager import ngrok_lifespan
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with ngrok_lifespan(app, 8000):
            yield
    
    app = FastAPI(lifespan=lifespan)
    ```
    """
    ngrok_manager = get_ngrok_manager()
    
    # Startup
    if ngrok_manager.is_development_mode():
        tunnel_url = ngrok_manager.start_tunnel(port)
        if tunnel_url:
            logger.info(f"🚀 Development server accessible at: {tunnel_url}")
            logger.info("🔗 Cloud Tasks can now reach your local server!")
        else:
            logger.warning("⚠️  ngrok tunnel failed. Cloud Tasks will not work with localhost.")
    
    try:
        yield
    finally:
        # Shutdown
        ngrok_manager.stop_tunnel()