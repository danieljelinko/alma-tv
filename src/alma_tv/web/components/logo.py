from fasthtml.common import *

def Logo():
    """Render the Alma TV Logo (Fruit Apple inside TV)."""
    svg = """
    <svg viewBox="0 0 100 100" style="width: 100%; height: 100%; filter: drop-shadow(0 0 5px rgba(255,255,255,0.2));">
        <!-- TV Frame -->
        <rect x="5" y="10" width="90" height="70" rx="15" ry="15" fill="none" stroke="rgba(255, 255, 255, 0.5)" stroke-width="4" />
        <!-- Antenna -->
        <path d="M 30 10 L 20 0 M 70 10 L 80 0" stroke="rgba(255, 255, 255, 0.5)" stroke-width="3" fill="none" stroke-linecap="round" />
        
        <!-- Fruit Apple Logo (Natural Shape) - Centered in TV -->
        <g transform="translate(50, 45) scale(0.25)">
            <path d="M -20 -40 C -30 -50 -40 -50 -45 -45 C -55 -35 -55 -15 -45 5 C -40 15 -30 20 -20 20 C -10 20 0 15 5 5 C 15 -15 15 -35 5 -45 C 0 -50 -10 -50 -20 -40 Z M -20 -40 C -20 -50 -15 -55 -10 -55" 
                  stroke="rgba(255, 255, 255, 0.9)" stroke-width="3" fill="rgba(255, 255, 255, 0.3)" stroke-linecap="round" stroke-linejoin="round"/>
            <!-- Leaf -->
            <path d="M -20 -40 Q -30 -55 -40 -50 Q -30 -45 -20 -40" fill="rgba(255, 255, 255, 0.8)" />
        </g>
    </svg>
    """
    return Div(
        NotStr(svg),
        style="position: absolute; top: 2vh; right: 2vw; width: 7vw; height: 7vw; z-index: 100; pointer-events: none; opacity: 1.0;"
    )
