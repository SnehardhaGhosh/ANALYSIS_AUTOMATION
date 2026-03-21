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