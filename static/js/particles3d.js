/**
 * Google Aura 3D Field for AI Data Analyst
 * Floating Numbers and Alphabets on Light Background
 */

let scene, camera, renderer, particles;
let mouseX = 0, mouseY = 0;

const characters = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const palette = [
    0xAECBFA, // Light Google Blue (Pastel)
    0xF28B82, // Light Google Red (Pastel)
    0xFDE293, // Light Google Yellow (Pastel)
    0xCEEAD6, // Light Google Green (Pastel)
];

function createTextTexture(char, color) {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');
    
    const hexColor = '#' + color.toString(16).padStart(6, '0');
    ctx.fillStyle = hexColor;
    ctx.font = '900 100px "Inter", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    ctx.fillText(char, 64, 64);

    const texture = new THREE.CanvasTexture(canvas);
    return texture;
}

function init() {
    const container = document.getElementById('canvas-container');
    if (!container) return;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 4000);
    camera.position.z = 1200;

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    const group = new THREE.Group();

    // Balanced density for light theme
    for (let i = 0; i < 800; i++) {
        const char = characters.charAt(Math.floor(Math.random() * characters.length));
        const color = palette[Math.floor(Math.random() * palette.length)];
        const texture = createTextTexture(char, color);
        
        const material = new THREE.SpriteMaterial({ 
            map: texture,
            transparent: true,
            opacity: Math.random() * 0.1 + 0.05 // Significantly reduced opacity for background feel
        });

        const sprite = new THREE.Sprite(material);
        
        sprite.position.x = Math.random() * 5000 - 2500;
        sprite.position.y = Math.random() * 5000 - 2500;
        sprite.position.z = Math.random() * 5000 - 2500;
        
        const scale = Math.random() * 80 + 80; // Larger characters
        sprite.scale.set(scale, scale, 1);
        
        sprite.userData = {
            floatSpeed: Math.random() * 1.0 + 0.3,
            driftFactor: Math.random() * 2
        };

        group.add(sprite);
    }

    particles = group;
    scene.add(particles);

    document.addEventListener('mousemove', onDocumentMouseMove);
    window.addEventListener('resize', onWindowResize);

    animate();
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function onDocumentMouseMove(event) {
    mouseX = (event.clientX - window.innerWidth / 2) * 0.1;
    mouseY = (event.clientY - window.innerHeight / 2) * 0.1;
}

function animate() {
    requestAnimationFrame(animate);

    if (particles) {
        particles.children.forEach(sprite => {
            sprite.position.y += sprite.userData.floatSpeed;
            if (sprite.position.y > 2500) sprite.position.y = -2500;
            
            sprite.position.x += Math.sin(Date.now() * 0.001 * sprite.userData.driftFactor) * 0.3;
        });

        particles.rotation.y += 0.0002;
    }

    camera.position.x += (mouseX - camera.position.x) * 0.05;
    camera.position.y += (-mouseY - camera.position.y) * 0.05;
    camera.lookAt(scene.position);

    renderer.render(scene, camera);
}

document.addEventListener('DOMContentLoaded', init);
