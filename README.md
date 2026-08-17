# Universal AI Dub

Proof-of-concept di un motore sostituibile **audio → STT → traduzione → TTS → audio**, progettato fin dall'inizio per elaborare piccoli chunk anziché file completi. Il solo obiettivo dell'MVP è misurare qualità, stabilità e latenza percepita con il microfono; non è un sistema di doppiaggio video.

## Analisi e scelte tecniche

L'architettura proposta è corretta. Due precisazioni minime sono indispensabili:

1. un transcript parziale non è stabile: viene mostrato in debug, ma soltanto un risultato finale attiva traduzione e TTS;
2. `audio_received_at` è il timestamp del primo chunk attribuito all'utterance. Il totale misura quindi dall'inizio del parlato catturato all'avvio reale dell'output, e include naturalmente la durata necessaria a determinare la fine dell'utterance.

Il POC usa:

- **Deepgram Nova-3 Live STT**, via WebSocket, perché accetta PCM continuamente e produce risultati interim/final con endpointing;
- **DeepL API**, perché la traduzione di una breve frase è una richiesta semplice e veloce (la traduzione non necessita streaming a livello di token in questo MVP);
- **ElevenLabs Flash v2.5**, endpoint HTTP streaming con output PCM, per ottenere il primo audio senza attendere il file completo;
- **sounddevice/PortAudio**, per input e output PCM a bassa complessità.

Sono tre account/key, un compromesso intenzionale per validare ogni fase con un servizio specializzato. Gli adapter astratti impediscono che questa scelta si propaghi nel motore.

### Rischi tecnici principali

- **Endpointing e qualità:** poco silenzio riduce la latenza ma può spezzare frasi; molto silenzio la aumenta. Il valore iniziale è 300 ms.
- **Crescita del ritardo:** il parlato italiano sintetizzato può durare più dell'originale. Questo MVP serializza i segmenti e non fa time-stretch/mixing, quindi sotto carico può accumulare coda.
- **Eco:** casse e microfono nello stesso ambiente possono reinserire il doppiaggio nello STT. Per il test sono consigliate cuffie.
- **Rete/provider:** jitter, rate limit e disconnessioni dominano la latenza. I timeout sono gestiti, ma il POC non riprende una sessione STT interrotta: va riavviato per non duplicare audio o testo.
- **Metriche:** `tts_first_audio_at` misura il primo byte PCM ricevuto e `playback_started_at` l'apertura effettiva dello stream. Non misura il tempo acustico del DAC.
- **Lingue:** i codici devono essere supportati da tutti e tre i provider; un HTTP/provider error è presentato in forma leggibile.

## Prerequisiti e installazione

- Python **3.11+**;
- PortAudio e un microfono/output audio funzionanti;
- Linux (Debian/Ubuntu): `sudo apt install libportaudio2 portaudio19-dev`;
- account Deepgram, DeepL ed ElevenLabs.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Compilare `.env` senza mai commetterlo:

```dotenv
DEEPGRAM_API_KEY=...
DEEPL_API_KEY=...
DEEPL_BASE_URL=https://api-free.deepl.com
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
```

Per DeepL Pro usare `https://api.deepl.com`. La voice ID deve indicare una voce ElevenLabs abilitata all'italiano.

## Avvio

Test esatto inglese → italiano (usare cuffie):

```bash
python -m src.main --source microphone --input-language en --output-language it
```

Con diagnostica (partial/final transcript, byte e buffer dei chunk, timestamp, latenze, errori provider):

```bash
python -m src.main --source microphone --input-language en --output-language it --debug
```

Interrompere con `Ctrl+C`. Il programma stampa per ogni finale testo originale/tradotto e latenze reali, poi numero segmenti, media, minimo e massimo della latenza totale. Non vengono creati valori simulati nella CLI.

## Pipeline e struttura

```text
MicrophoneSource (PCM16, chunk da 100 ms)
  → DeepgramSpeechRecognizer (partial + final)
  → DeepLTranslator (solo final)
  → ElevenLabsSpeechSynthesizer (stream PCM 24 kHz)
  → SpeakerSink
```

```text
src/audio/       AudioSource, MicrophoneSource, AudioSink/SpeakerSink
src/ai/          SpeechRecognizer, Translator, SpeechSynthesizer + provider
src/pipeline/    DubPipeline e Metrics
src/config.py    configurazione ambiente validata
src/main.py      CLI e composizione degli adapter
tests/           fake provider e unit test senza rete/audio reale
```

Per segmento si conservano `audio_received_at`, `stt_completed_at`, `translation_completed_at`, `tts_first_audio_at` e `playback_started_at`. STT, traduzione, TTS e totale derivano esclusivamente da questi orologi monotonic reali.

## Test

```bash
python -m compileall -q src tests
pytest -q
```

I test usano adapter fake: non richiedono API key, rete, microfono o altoparlanti.

## Limitazioni MVP

Il motore elabora finali in sequenza; non include retry automatici (evita duplicazioni), VAD locale, preservazione audio originale, mixer, cancellazione eco, diarizzazione, lip-sync, voice cloning, GUI, video, hardware/capture/HDMI né modelli offline. I transcript finali troppo lunghi aumentano la latenza; quelli troppo brevi riducono il contesto di traduzione.

## Roadmap (non implementata)

Sorgenti intercambiabili (capture/network/HDMI), VAD e buffer adattivo, traduzione contestuale, coda concorrente con backpressure, separazione dialoghi/musica/effetti, speaker e voci multiple, mixer, sincronizzazione A/V, modelli locali/GPU, confronto cloud/offline e costo per ora. HDCP e integrazioni specifiche restano fuori dal POC.
