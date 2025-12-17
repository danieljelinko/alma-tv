"""Video Player component for Web App."""

from fasthtml.common import *
from alma_tv.web.state import state
from alma_tv.web.components.logo import Logo

def PlayerView():
    """Render the Video Player view."""
    current_video = state.next_video()
    
    if not current_video:
        # Playlist finished, state is now FEEDBACK
        # Return FeedbackView directly to avoid "Session Finished" flash
        from alma_tv.web.components.feedback import FeedbackView
        return FeedbackView()
        
    video_path = current_video.get("path")
    title = current_video.get("title", "Unknown Video")
    
    return Div(
        Video(
            Source(src=f"/stream?path={video_path}", type="video/mp4"),
            autoplay=True,
            controls=True,
            style="width: 100%; height: 100%; object-fit: contain;",
            # When video ends, trigger next video
            hx_get="/player/next",
            hx_trigger="ended",
            hx_target="body",
            hx_swap="innerHTML",
            id="video-player"
        ),
        # Unmute Overlay
        Div(
            H1("🔊 Click to Unmute", style="color: white; font-size: 3rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); pointer-events: none;"),
            id="unmute-overlay",
            onclick="document.getElementById('video-player').muted = false; this.style.display = 'none';",
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.4); cursor: pointer; z-index: 10;"
        ),
        # Debug Info
        Div(
            f"Video {state.current_video_index} / {len(state.current_playlist)}",
            style="position: absolute; top: 10px; right: 10px; color: rgba(255,255,255,0.5); font-family: monospace; z-index: 5;"
        ),
        # Script to handle autoplay and unmute overlay
        Script("""
            var video = document.getElementById('video-player');
            var overlay = document.getElementById('unmute-overlay');
            
            // Log when video loads successfully
            video.addEventListener('loadedmetadata', function() {
                console.log('Video loaded:', video.src);
                console.log('Duration:', video.duration);
            });
            
            // Handle errors
            video.addEventListener('error', function(e) {
                console.error('Video error:', e);
                console.error('Error code:', video.error ? video.error.code : 'unknown');
                console.error('Error message:', video.error ? video.error.message : 'unknown');
                
                // Display error to user
                overlay.innerHTML = '<h1 style="color: red;">⚠️ Video Error - Skipping...</h1>';
                overlay.style.display = 'flex';
                
                // Auto-skip after 2 seconds
                setTimeout(function() {
                    htmx.ajax('GET', '/player/next', {target: 'body', swap: 'innerHTML'});
                }, 2000);
            });
            
            // Try to play with sound
            video.play().then(() => {
                // If successful, hide overlay
                overlay.style.display = 'none';
            }).catch(e => {
                console.log('Autoplay with sound blocked, muting and trying again:', e);
                video.muted = true;
                video.play().then(() => {
                    // Playing muted, show overlay
                    overlay.style.display = 'flex';
                }).catch(err => {
                    console.error('Failed to play even when muted:', err);
                });
            });
            
            // Hide overlay on interaction
            overlay.addEventListener('click', function() {
                video.muted = false;
                this.style.display = 'none';
            });
        """),
        id="player-container",
        style="width: 100vw; height: 100vh; background: black; display: flex; align-items: center; justify-content: center; position: relative;"
    ), Logo()
