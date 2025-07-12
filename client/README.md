# VISA Interview Training System - Client

This is the client-side application for the VISA Interview Training System. It provides a user interface for simulating visa interviews with audio-based interaction.

## Features

- Audio-based interaction with text-to-speech questions and microphone recording for answers
- Multiple visa type options (tourist or student)
- Choice of AI interviewer voices
- Different subscription tiers with varying numbers of questions
- Real-time audio streaming to the backend for processing
- Comprehensive results with performance metrics and feedback

## Getting Started

### Prerequisites

- Node.js 16.x or higher
- npm 8.x or higher

### Installation

1. Clone the repository
2. Navigate to the client directory:
   ```bash
   cd d:/AIML/VISA/client
   ```
3. Install dependencies:
   ```bash
   npm install
   ```

### Development

To start the development server:

```bash
npm run dev
```

The application will be available at http://localhost:5173 by default.

### Building for Production

To build the application for production:

```bash
npm run build
```

The built files will be available in the `dist` directory.

## Project Structure

- `src/` - Source code directory
  - `components/` - React components
  - `App.jsx` - Main application component
  - `main.jsx` - Application entry point
  - `index.css` - Global styles

## Technology Stack

- React.js - Frontend UI library
- Vite - Build tool and development server
- WebSockets - For real-time audio streaming
- Web Audio API - For microphone access and recording
