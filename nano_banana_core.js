/**
 * Nano Banana 2 - 3D UI & Scroll-Stop Generation Framework
 * GSAP v2 Implementation for rapid front-end building.
 */

class NanoBananaCore {
    constructor(config = {}) {
        this.theme = config.theme || 'dark';
        this.animationSpeed = config.animationSpeed || 'fast';
        console.log(`[NanoBanana2] Initialized with theme: ${this.theme}, GSAP mode enabled.`);
    }

    /**
     * Generates a 3D glassmorphism card component with vanilla tilt effect.
     */
    generate3DCard(data) {
        return `
        <div class="nb2-3d-card" data-tilt data-tilt-max="15" data-tilt-speed="400" data-tilt-perspective="1000" style="backdrop-filter: blur(20px); background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 2rem;">
            <h3 style="font-family: 'Space Grotesk', sans-serif;">${data.title}</h3>
            <p style="color: #99A1AF;">${data.description}</p>
        </div>
        `;
    }

    /**
     * Generates a structural GSAP ScrollTrigger timeline for a generic section.
     */
    generateGSAPScrollAnim(sectionId, elementClass) {
        return `
        gsap.to(".${elementClass}", {
            scrollTrigger: {
                trigger: "#${sectionId}",
                start: "top center",
                end: "bottom center",
                scrub: 1,
                toggleActions: "play reverse play reverse"
            },
            y: -50,
            opacity: 1,
            stagger: 0.1,
            duration: 1,
            ease: "power3.out"
        });
        `;
    }

    /**
     * Renders a full GSAP-integrated dashboard layout
     */
    renderDashboard(layout) {
        console.log(`[NanoBanana2] Rendering dashboard layout: ${layout}`);
        return `
        <div class='nb2-dashboard ${this.theme}-theme'>
            <!-- GSAP Content Container -->
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js"></script>
        `;
    }
}

module.exports = NanoBananaCore;
