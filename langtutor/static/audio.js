let audioCtx;
let source;
let mediaRecorder;
let mediaStream;
let audioBuffers = [];
let startTime = 0;
let pauseTime = 0;
let isPlaying = false;
let isPaused = false;
let stopPlaying = false;
let recordedChunks = [];


$(document).ready(function() {
    audioBuffers = [];
    startTime = 0;
    pauseTime = 0;
    isPlaying = false;
    isPaused = false;
    stopPlaying = false;
    recordedChunks = [];

    // setInterval(function () {
    //     if (audioCtx !== undefined) {loadAudioFromQueue();}
    // }, 1000);
});


function initAudio() {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
}


// function loadAudioFromQueue() {
//     try {
//         if (!stopPlaying) {
//             $.get('/get_next_from_audio_queue', async function (response) {
//                 if (!response['empty']) {
//                     const file_url = response['file_url'];
//                     console.log('Fetching audio file:', file_url);
//                     const fetchResponse = await fetch(file_url);
//                     const arrayBuffer = await fetchResponse.arrayBuffer();

//                     // Decode the audio data from the MP3 file
//                     audioBuffers.push(await audioCtx.decodeAudioData(arrayBuffer));
//                     if (!isPlaying && !isPaused && !stopPlaying) {
//                         playAudio();
//                     }
//                 }
//             });
//         }
//     } catch (error) {
//         console.error('Error loading audio:', error);
//     }
// }

async function addAudiotoQueue(audio_url) {
    try {
        if (!stopPlaying) {
            const file_url = audio_url;
            console.log('Fetching audio file:', file_url);
            
            // Fetch audio file asynchronously
            const fetchResponse = await fetch(file_url);
            const arrayBuffer = await fetchResponse.arrayBuffer();

            // Decode the audio data from the MP3 file
            audioBuffers.push(await audioCtx.decodeAudioData(arrayBuffer));

            // Check if audio is not already playing or paused, then play audio
            if (!isPlaying && !isPaused && !stopPlaying) {
                playAudio();
            }
        }
    } catch (error) {
        console.error('Error loading audio:', error);
    }
}


function playAudio() {
    if (!isPlaying) {
        isPlaying = true;
        isPaused = false;
        stopPlaying = false;
        source = audioCtx.createBufferSource();
        source.buffer = audioBuffers[0];
        source.connect(audioCtx.destination);

        // Set up an event handler to detect when the audio has finished playing
        source.onended = function () {
            isPlaying = false;
            if (!isPaused) {
                audioBuffers.shift();
                if (audioBuffers.length > 0) {
                    startTime = 0;
                    pauseTime = 0;
                    playAudio();
                } else {
                    stopAudio();
                }
            }
        };

        // Start the source to play the audio
        let offset = pauseTime;
        source.start(0, offset);
        startTime = audioCtx.currentTime - offset;
        updateUIByAudioStatus(isPlaying);
    }
}


async function playSingleAudioFile(file_url) {
    if (audioCtx === undefined) {
        initAudio();
    }
    const fetchResponse = await fetch(file_url);
    const arrayBuffer = await fetchResponse.arrayBuffer();
    const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
    source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioCtx.destination);
    source.start()
}


function pauseAudio() {
    isPaused = true;
    source.stop();
    pauseTime = audioCtx.currentTime - startTime;
    isPlaying = false;
}


function stopAudio() {
    stopPlaying = true;
    isPlaying = false;
    isPaused = false;
    // source.stop();
    synth.cancel()
    audiows.close()
    
    audioBuffers = [];
    pauseTime = 0;  // Reset the pause time so the audio starts from the beginning next time
    startTime = 0;
    updateUIByAudioStatus(isPlaying);
}


function startRecording() {
    stopAudio();
    var recordButton = $("#record-button");
    var langToggleButton = $('#lang-toggle-button'); // Select the lang-toggle-button

    recordButton.removeClass('btn-secondary off').addClass('btn-danger on');
    langToggleButton.removeClass('btn-secondary off').addClass('btn-danger on');
    // toggleLoadingIcon('show');
    recognition.start();
    return
    return new Promise(async (resolve, reject) => {
    try {
        stopAudio();
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(mediaStream);

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            const blob = new Blob(recordedChunks, { type: 'audio/mpeg-3' });
            recordedChunks = [];
            resolve(blob);
        };

        mediaRecorder.onerror = (event) => {
            reject(event.error);
        };

        mediaRecorder.start();

        } catch (error) {
            console.error('Error starting recording:', error);
            reject(error);
        }
    });
}


function stopRecording() {
    recognition.stop();
    var recordButton = $("#record-button");
    var langToggleButton = $('#lang-toggle-button'); // Select the lang-toggle-button
    recordButton.removeClass('btn-danger on').addClass('btn-secondary off');
    langToggleButton.removeClass('btn-danger on').addClass('btn-secondary off');
    // toggleLoadingIcon('hide');
    // if (mediaRecorder) {
    //     mediaRecorder.stop();
    // }
    // if (mediaStream) {
    //     mediaStream.getTracks().forEach(track => track.stop());
    // }
}


async function uploadAudio(blob) {
    let filename = null;
    try {
        console.log('Uploading recording...');
        const formData = new FormData();
        formData.append('file', blob, 'recording.mp3');
        console.log('FormData created:', formData, 'Blob size:', blob.size);
        for (let [key, value] of formData.entries()) {
            console.log(key, value);
        }

        const response = await fetch(upload_endpoint, {
            method: 'POST',
            body: formData,
        });
        const data = await response.json();
        filename = data.filename;
        if (response.ok && filename !== null) {
            filename = data.filename;
        } else if (response.ok && filename === null) {
            console.error('Error uploading audio: no file found on request');
        } else {
            console.error('Error uploading audio:', response.statusText);
        }
    } catch (error) {
        console.error('Error uploading audio:', error);
    }
    return filename;
}


function updateUIByAudioStatus(is_playing) {

    var record_button = $('#record-button');
    var record_icon = $('#record-icon');
    var lang_button = $('#lang-toggle-button');
    var lang_text = $('#lang-text');
    var pause_icon = $('#pause-icon');

    if (is_playing && record_button.attr('name') === 'record') {
        record_button.attr('name', 'stop');
        record_button.attr('title', 'Stop Audio');
        lang_button.attr('name', 'pause');
        lang_button.attr('title', 'Pause Audio');

        record_icon.removeClass('fas');
        record_icon.removeClass('fa-microphone');
        record_icon.addClass('fa-solid');
        record_icon.addClass('fa-stop');

        lang_text.css('display', 'none');
        pause_icon.css('display', 'block');
        pause_icon.removeClass('fa-play');
        pause_icon.addClass('fa-pause');

    } else if (!is_playing && record_button.attr('name') === 'stop') {
        record_button.attr('name', 'record');
        record_button.attr('title', 'Record Message [Alt+R]');
        lang_button.attr('name', 'lang-record');
        lang_button.attr('title', 'Switch Recording Language [Alt+L]');

        record_icon.addClass('fas');
        record_icon.addClass('fa-microphone');
        record_icon.removeClass('fa-solid');
        record_icon.removeClass('fa-stop');

        lang_text.css('display', 'block');
        pause_icon.css('display', 'none');
    }
}




// Initialize Web Speech API recognition with French language
const recognition = new webkitSpeechRecognition();
recognition.lang = 'fr-FR'; // Set language to French
recognition.continuous=true;
recognition.interimResults = true; // Enable interim results for capturing real-time speech

// Set up event handlers
recognition.onstart = function() {
  console.log('Speech recognition started');
};

recognition.onsoundend = function() {
  console.log('Speech recognition sound ended');

//   recognition.start()
};

recognition.onend = function() {
    console.log('Speech recognition ended');
  
    // recognition.start()
  };

var audio2send=""
var lastAudioBounce=-1
function sendBounce(){
    addMyMessage(audio2send)
    audio2send=""
    stopRecording()
}
recognition.onresult = function(event) {
  // Handle speech recognition results
//   if (audio2send==""){
//     audio2send=$('#message-input').val();
//   }
  const result = event.results[event.results.length - 1];
  const isFinal = result.isFinal;
  const transcript = result[0].transcript;
  clearTimeout(lastAudioBounce)
  if (isFinal) {
    console.log('Finalized speech:', transcript);
    audio2send+=transcript+". "

    lastAudioBounce=setTimeout(sendBounce,3000)

    

    $('#message-input').val('');
    
    // User finished speaking, do something
  } else {
    console.log('Interim speech:', transcript);
    $('#message-input').val(transcript);
    // User is speaking, do something
  }
};

// Start speech recognition



const synth = window.speechSynthesis;

const selectedOption ="Google français";
  
      
var voice=undefined;

var speakQ=[]
function speak(txt,end) {
    if (!$("#record-button").hasClass("off"))
        return
    $('#tmp').html(txt)
    txt=$('#tmp').text()
    if (voice==undefined){
        voices = synth.getVoices()
        for (let i = 0; i < voices.length; i++) {
        if (voices[i].name === selectedOption) {
            var voice=voices[i];
            
            break;
        }
        }

    }
    speakQ.push(txt)
    if (synth.speaking) {
      console.log("speechSynthesis.speaking");
    //   return;
    }
    // while(speakQ.length>0)
    {
        speakQ.pop()
        // txt=
    if (txt !== "") {
      const utterThis = new SpeechSynthesisUtterance(txt);
  
      utterThis.onend = function (event) {
        console.log("SpeechSynthesisUtterance.onend");
        if (end)
            startRecording()

      };
  
      utterThis.onerror = function (event) {
        console.log("SpeechSynthesisUtterance.onerror");
      };
      utterThis.voice=voice;
      utterThis.lang = "fr-FR";
      utterThis.pitch = 1;
      utterThis.rate = 1;
      synth.speak(utterThis);
    }
}
  }