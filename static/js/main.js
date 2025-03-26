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
    
    // Create stop button element (hidden by default)
    const stopButton = document.createElement('button');
    stopButton.id = 'stop-button';
    stopButton.className = 'stop-button';
    stopButton.innerHTML = '<i class="fas fa-stop"></i>';
    stopButton.title = 'Stop speaking';
    stopButton.style.display = 'none';
    
    // Add the stop button after the mic button
    micButton.parentNode.insertBefore(stopButton, micButton.nextSibling);

    // MediaRecorder variables
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    let stream;
    
    // Keep track of microphone stream to avoid requesting permission multiple times
    let microphoneStream = null;
    
    // Flag for speech state
    let isSpeaking = false;

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
    
    // Function to update speaking UI
    function updateSpeakingUI(speaking) {
        isSpeaking = speaking;
        
        if (speaking) {
            // Show stop button when speaking
            stopButton.style.display = 'block';
            audioStatus.textContent = 'Playing response...';
        } else {
            // Hide stop button when not speaking
            stopButton.style.display = 'none';
            audioStatus.textContent = 'Ready';
        }
    }

    // Function to get microphone access once
    async function getMicrophoneAccess() {
        if (microphoneStream) {
            return microphoneStream;
        }
        
        try {
            // Request microphone permission
            microphoneStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            return microphoneStream;
        } catch (error) {
            console.error('Error accessing microphone:', error);
            audioStatus.textContent = 'Microphone access denied';
            alert('Please allow microphone access to use voice input');
            throw error;
        }
    }

    // Function to start recording
    async function startRecording() {
        try {
            // First, stop any ongoing speech
            stopSpeaking();
            
            audioStatus.textContent = 'Preparing to record...';
            
            // Get microphone access (will use cached stream if available)
            stream = await getMicrophoneAccess();
            
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
            audioStatus.textContent = 'Error starting recording';
        }
    }

    // Function to stop recording
    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            // Don't stop the stream, keep it for future recordings
            audioStatus.textContent = 'Processing...';
            updateRecorderUI(false);
        }
    }

    // Function to stop speaking
    function stopSpeaking() {
        console.log("Stopping speech");
        
        // Get the existing audio element
        const existingAudio = document.getElementById('response-audio');
        if (existingAudio) {
            // Remove source and pause
            existingAudio.src = "";
            existingAudio.pause();
        }
        
        // Update UI
        updateSpeakingUI(false);
        
        // Signal the server
        fetch('/cancel_response', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        }).catch(error => {
            console.error('Error canceling response:', error);
        });
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
            
            // Get the existing audio element
            const audioElement = document.getElementById('response-audio');
            if (audioElement && data.audio_data) {
                // Update UI to show stop button
                updateSpeakingUI(true);
                
                // Set up the audio element
                audioElement.src = data.audio_data;
                
                audioElement.oncanplaythrough = function() {
                    audioElement.play();
                };
                
                audioElement.onended = function() {
                    updateSpeakingUI(false);
                };
                
                audioElement.onerror = function() {
                    updateSpeakingUI(false);
                    audioStatus.textContent = 'Error playing audio';
                };
            }
            
            serverStatus.textContent = 'Connected';
        } catch (error) {
            console.error('Error processing query:', error);
            serverStatus.textContent = 'Error';
            updateSpeakingUI(false);
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
        // If already recording, stop recording
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    });
    
    // Stop button click handler
    stopButton.addEventListener('click', function() {
        stopSpeaking();
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
            // Stop any ongoing speech
            stopSpeaking();
            
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
    
    // Request microphone access at page load to prepare for later use
    getMicrophoneAccess().catch(err => {
        // Don't show the alert here, as we'll handle it when the user clicks the mic button
        console.warn('Initial microphone access request failed:', err);
    });
});