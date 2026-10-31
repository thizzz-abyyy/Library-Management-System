// Apex Library Management System - Interactive Camera QR Code Scanner

let html5QrCode = null;

function startCameraScanner(readerElementId, onScanSuccessCallback) {
    const readerDiv = document.getElementById(readerElementId);
    if (!readerDiv) return;

    if (html5QrCode) {
        html5QrCode.stop().then(() => {
            html5QrCode = null;
        }).catch(err => console.error("Error stopping existing scanner", err));
    }

    html5QrCode = new Html5Qrcode(readerElementId);
    const config = { fps: 10, qrbox: { width: 250, height: 250 } };

    html5QrCode.start(
        { facingMode: "environment" },
        config,
        (decodedText, decodedResult) => {
            console.log("QR Decoded:", decodedText);
            // Beep audio feedback
            playBeep();
            
            // Stop camera on success
            html5QrCode.stop().then(() => {
                html5QrCode = null;
            }).catch(e => console.log(e));

            // Execute callback
            if (typeof onScanSuccessCallback === 'function') {
                onScanSuccessCallback(decodedText);
            }
        },
        (errorMessage) => {
            // Scanning in progress
        }
    ).catch(err => {
        console.error("Camera access failed", err);
        const errAlert = document.getElementById('cameraErrorMessage');
        if (errAlert) {
            errAlert.classList.remove('d-none');
            errAlert.textContent = "Camera permission not granted or no camera found. You can enter or paste the ID/ISBN directly.";
        }
    });
}

function stopCameraScanner() {
    if (html5QrCode) {
        html5QrCode.stop().then(() => {
            html5QrCode = null;
        }).catch(err => console.error(err));
    }
}

function playBeep() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.type = "sine";
        osc.frequency.value = 880;
        gain.gain.value = 0.1;
        osc.start();
        setTimeout(() => {
            osc.stop();
        }, 150);
    } catch (e) {
        // AudioContext not available or blocked
    }
}

// Helper to parse QR payload
function parseQrPayload(text) {
    // E.g. "BOOK|ID:1|ISBN:978-0132350884|TITLE:Clean Code"
    // E.g. "STUDENT|ID:STU-2026-001|NAME:Alexander Hayes"
    if (text.startsWith("BOOK|")) {
        const parts = text.split("|");
        const obj = { type: 'book' };
        parts.forEach(p => {
            if (p.startsWith("ID:")) obj.id = p.replace("ID:", "");
            if (p.startsWith("ISBN:")) obj.isbn = p.replace("ISBN:", "");
            if (p.startsWith("TITLE:")) obj.title = p.replace("TITLE:", "");
            if (p.startsWith("LOC:")) obj.location = p.replace("LOC:", "");
        });
        return obj;
    } else if (text.startsWith("STUDENT|")) {
        const parts = text.split("|");
        const obj = { type: 'student' };
        parts.forEach(p => {
            if (p.startsWith("ID:")) obj.id = p.replace("ID:", "");
            if (p.startsWith("NAME:")) obj.name = p.replace("NAME:", "");
        });
        return obj;
    }
    return { type: 'raw', value: text };
}

