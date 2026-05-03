// Chat functionality
async function sendQuery() {
    const input = document.getElementById("query");
    const chatBox = document.getElementById("chat-box");

    let query = input.value.trim();

    if (!query) {
        alert("Please enter a query");
        return;
    }

    // Display user message
    chatBox.innerHTML += `<div style="padding:12px; margin:10px 0; text-align:right; margin-left:60px;">
        <div style="background:#2196f3; color:white; padding:10px 14px; border-radius:12px; display:inline-block; max-width:500px; word-wrap:break-word; text-align:left; font-size:14px; line-height:1.5;">
            ${query}
        </div>
    </div>`;

    input.value = "";

    try {
        const response = await fetch("/ask", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ query: query })
        });

        const data = await response.json();

        if (data.error) {
            chatBox.innerHTML += `<div style="padding:12px; color:#d32f2f; background:#ffebee; border-radius:6px; margin:10px 0; margin-right:60px; font-size:14px;">❌ ${data.error}</div>`;
        } else if (data.response) {
            // Display AI response with clean styling
            chatBox.innerHTML += `<div style="padding:12px; margin:10px 0; margin-right:60px;">
                <div style="background:#f0f0f0; padding:12px 14px; border-radius:12px; font-size:14px; line-height:1.6; color:#333;">
                    ${data.response.replace(/\n/g, '<br>')}
                </div>
            </div>`;
        }

    } catch (error) {
        chatBox.innerHTML += `<div style="padding:12px; color:#d32f2f; background:#ffebee; border-radius:6px; margin:10px 0; margin-right:60px; font-size:14px;">❌ Error: ${error.message}</div>`;
    }

    // Auto scroll
    chatBox.scrollTop = chatBox.scrollHeight;
}


// Optional: handle Enter key
document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("query");

    if (input) {
        input.addEventListener("keypress", function (e) {
            if (e.key === "Enter") {
                sendQuery();
            }
        });
    }
});


// ============================================================
//  GLOBAL: Single-click protection for all navigation buttons
// ============================================================
(function () {
    // Inject a slim top-loading bar into every page
    const bar = document.createElement('div');
    bar.id = 'nav-progress-bar';
    bar.style.cssText = [
        'position:fixed', 'top:0', 'left:0', 'width:0%', 'height:3px',
        'background:linear-gradient(90deg,#1a73e8,#34a853)',
        'z-index:9999', 'transition:width 0.3s ease', 'opacity:0',
        'pointer-events:none'
    ].join(';');
    document.body.prepend(bar);

    function startBar() {
        bar.style.opacity = '1';
        bar.style.width = '70%';
        setTimeout(() => { bar.style.width = '90%'; }, 400);
    }

    // Lock a button (disable + show spinner text)
    function lockBtn(btn) {
        if (btn.dataset.locked) return false;   // already locked
        btn.dataset.locked = '1';
        btn.disabled = true;
        const icon = btn.querySelector('i');
        if (icon && !icon.classList.contains('fa-spinner')) {
            icon.className = 'fas fa-spinner fa-spin';
        }
        return true;
    }

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('button[type="submit"], a.btn, button.btn');
        if (!btn) return;

        // Skip buttons with data-no-lock attribute
        if (btn.dataset.noLock !== undefined) return;

        // Skip already-disabled buttons
        if (btn.disabled && !btn.dataset.locked) return;

        const isLink = btn.tagName === 'A';
        const isSubmit = btn.type === 'submit';

        if (isSubmit) {
            // Let form submit handle locking itself if it has custom handler
            // but still start the nav bar
            startBar();
        } else if (isLink && btn.href && !btn.href.startsWith('#')) {
            lockBtn(btn);
            startBar();
        } else if (!isLink) {
            // Generic button
            lockBtn(btn);
            startBar();
        }
    }, true);

    // Complete the bar on page unload (navigating away)
    window.addEventListener('beforeunload', () => {
        bar.style.width = '100%';
        setTimeout(() => { bar.style.opacity = '0'; }, 300);
    });
})();