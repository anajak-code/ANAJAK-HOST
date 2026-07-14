const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot');
const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const logConsole = document.getElementById('log-console');

// Function to add logs
function addLog(message) {
    const time = new Date().toLocaleTimeString();
    logConsole.innerHTML += `[${time}] ${message}<br>`;
    logConsole.scrollTop = logConsole.scrollHeight; // Auto scroll to bottom
}

// Check Status on Load
async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        updateUI(data.running, data.bot_status);
    } catch (error) {
        console.error('Error fetching status:', error);
        statusText.innerText = "Connection Error";
    }
}

// Update UI based on status
function updateUI(isRunning, statusMsg) {
    if (isRunning) {
        statusText.innerText = statusMsg || "Online";
        statusDot.className = "dot online";
        btnStart.disabled = true;
        btnStop.disabled = false;
    } else {
        statusText.innerText = "Offline";
        statusDot.className = "dot offline";
        btnStart.disabled = false;
        btnStop.disabled = true;
    }
}

// Control Bot (Start/Stop)
async function controlBot(action) {
    addLog(`Sending command: ${action.toUpperCase()}...`);
    
    try {
        const response = await fetch(`/api/${action}`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            addLog(`Success: ${data.message}`);
            // Wait a bit then check status again to update UI correctly
            setTimeout(checkStatus, 2000); 
        } else {
            addLog(`Error: ${data.message}`);
        }
    } catch (error) {
        addLog(`Network Error: ${error}`);
    }
}

// Initial check
checkStatus();
addLog("System Ready.");
