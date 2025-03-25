document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const micButton = document.getElementById('mic-button');
    const statusIndicator = document.getElementById('status-indicator');
    const textInput = document.getElementById('text-input');
    const sendButton = document.getElementById('send-button');
    const chatContainer = document.getElementById('chat-container');
    const audioElement = document.getElementById('response-audio');
    const audioStatus = document.querySelector('#audio-status span');
    const serverStatus = document.querySelector('#server-status span');

    // MediaRecorder variables
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    let stream;

    // Function to update recorder UI
    function updateRecorderUI(recording) {
        isRecording = recording;
        
        if (recording) {
            micButton.classList.add('recording');
            statusIndicator.textContent = 'Listening...';
            micButton.innerHTML = '<i class="fas fa-stop"></i>';
        } else {
            micButton.classList.remove('recording');
            statusIndicator.textContent = 'Click to speak';
            micButton.innerHTML = '<i class="fas fa-microphone"></i>';
        }
    }

    // Function to start recording
    async function startRecording() {
        try {
            audioStatus.textContent = 'Requesting microphone access...';
            
            // Request microphone permission
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Create media recorder
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            // Add event listeners for audio data
            mediaRecorder.addEventListener('dataavailable', event => {
                audioChunks.push(event.data);
            });
            
            // When recording stops, process audio
            mediaRecorder.addEventListener('stop', processAudio);
            
            // Start recording
            mediaRecorder.start();
            audioStatus.textContent = 'Recording...';
            
            // Update UI
            updateRecorderUI(true);
        } catch (error) {
            console.error('Error starting recording:', error);
            audioStatus.textContent = 'Microphone access denied';
            alert('Please allow microphone access to use voice input');
        }
    }

    // Function to stop recording
    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            stream.getTracks().forEach(track => track.stop());
            audioStatus.textContent = 'Processing...';
            updateRecorderUI(false);
        }
    }

    // Function to process recorded audio
    async function processAudio() {
        try {
            audioStatus.textContent = 'Processing audio...';
            
            // Create blob from audio chunks
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            
            // Convert blob to base64
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            
            reader.onloadend = async function() {
                const base64Audio = reader.result;
                
                // Send to backend for transcription
                const response = await fetch('/transcribe', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ audio: base64Audio })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to transcribe audio');
                }
                
                const data = await response.json();
                
                if (data.text) {
                    // Add user message to chat
                    addMessageToChat('user', data.text);
                    
                    // Process the query
                    await processQuery(data.text);
                } else {
                    audioStatus.textContent = 'Could not understand audio';
                }
            };
        } catch (error) {
            console.error('Error processing audio:', error);
            audioStatus.textContent = 'Error processing audio';
        }
    }

    // Function to process text query
    // Update the processQuery function in main.js to handle base64 audio

// Function to process text query
async function processQuery(text) {
    try {
        audioStatus.textContent = 'Getting response...';
        serverStatus.textContent = 'Processing...';
        
        // Send query to backend
        const response = await fetch('/process_query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: text })
        });
        
        if (!response.ok) {
            throw new Error('Failed to process query');
        }
        
        const data = await response.json();
        
        // Add bot message to chat
        addMessageToChat('bot', data.text);
        
        // Play audio response directly from base64 data
        if (data.audio_data) {
            audioElement.src = data.audio_data;
            audioElement.oncanplaythrough = function() {
                audioStatus.textContent = 'Playing response...';
                audioElement.play();
            };
            audioElement.onended = function() {
                audioStatus.textContent = 'Ready';
            };
        }
        
        serverStatus.textContent = 'Connected';
    } catch (error) {
        console.error('Error processing query:', error);
        serverStatus.textContent = 'Error';
        addMessageToChat('bot', 'Sorry, I encountered an error processing your request.');
    }
}
    // Function to add message to chat
    function addMessageToChat(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const paragraph = document.createElement('p');
        paragraph.textContent = text;
        
        contentDiv.appendChild(paragraph);
        messageDiv.appendChild(contentDiv);
        chatContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Mic button click handler - toggle recording
    micButton.addEventListener('click', function() {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    });

    // Send button click handler
    sendButton.addEventListener('click', function() {
        sendTextInput();
    });

    // Text input keyboard handler
    textInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendTextInput();
        }
    });

    // Function to send text input
    function sendTextInput() {
        const text = textInput.value.trim();
        if (text) {
            addMessageToChat('user', text);
            processQuery(text);
            textInput.value = '';
        }
    }

    // Check server health on load
    async function checkServerHealth() {
        try {
            const response = await fetch('/health');
            if (response.ok) {
                serverStatus.textContent = 'Connected';
            } else {
                serverStatus.textContent = 'Disconnected';
            }
        } catch (error) {
            serverStatus.textContent = 'Disconnected';
        }
    }

    // Initialize
    checkServerHealth();
    audioStatus.textContent = 'Ready';
});