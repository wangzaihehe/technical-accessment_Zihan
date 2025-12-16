# Website Authentication Component Detector

An AI-powered tool for automatically detecting login forms and authentication components in web pages.

## Architecture

This project uses a **Python backend** (FastAPI) and a **React frontend** (Vite):

- **Backend**: Python FastAPI server running on port 8000
- **Frontend**: React application with Vite running on port 5173

## Features

- ✅ **Web Scraper**: Automatically scrapes website HTML content
- ✅ **Authentication Component Detection**: Intelligently identifies login forms, username inputs, password inputs, and other authentication elements
- ✅ **Dynamic URL Input**: Supports inputting any website URL for detection
- ✅ **Batch Detection**: Supports detecting multiple predefined websites simultaneously
- ✅ **Structured Output**: Returns HTML snippets containing authentication components and detailed information

## Tech Stack

### Backend
- **Framework**: FastAPI
- **HTTP Client**: httpx
- **HTML Parser**: BeautifulSoup4
- **Language**: Python 3.8+

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Language**: TypeScript

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start the backend server:
```bash
python main.py
```

The API will be available at [http://localhost:8000](http://localhost:8000)

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at [http://localhost:5173](http://localhost:5173)

## Usage

### 1. Dynamic URL Detection

1. Enter the website URL you want to detect in the input box on the main page
2. Click the "Detect" button
3. View the detection results, including:
   - Whether authentication components were found
   - Form HTML snippet
   - Username input field
   - Password input field
   - Submit button
   - Form method and action

### 2. Predefined Website Detection

1. Click the "Detect 5 Predefined Websites" button
2. The system will automatically detect the following websites:
   - GitHub login page
   - Stack Overflow login page
   - LinkedIn login page
   - Quora login page
   - Dropbox login page
3. View batch detection results

## API Endpoints

### POST /api/scrape

Detect authentication components for a single website

**Request Body:**
```json
{
  "url": "https://example.com/login"
}
```

**Response:**
```json
{
  "url": "https://example.com/login",
  "success": true,
  "authComponent": {
    "found": true,
    "htmlSnippet": "<form>...</form>",
    "formElement": "<form method=\"post\">...</form>",
    "usernameInput": "<input type=\"text\" name=\"username\">",
    "passwordInput": "<input type=\"password\" name=\"password\">",
    "submitButton": "<button type=\"submit\">Login</button>",
    "method": "POST",
    "action": "https://example.com/login"
  }
}
```

### GET /api/predefined

Detect 5 predefined websites

**Response:**
```json
{
  "results": [
    {
      "url": "https://github.com/login",
      "success": true,
      "authComponent": { ... }
    },
    ...
  ]
}
```

## Project Structure

```
.
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── .gitignore
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Main React component
│   │   ├── main.tsx        # React entry point
│   │   └── index.css       # Global styles
│   ├── package.json        # Node.js dependencies
│   ├── vite.config.ts      # Vite configuration
│   └── index.html
└── README.md
```

## Detection Algorithm

The authentication component detection algorithm will:

1. **Find Password Input Fields**: Search for all `<input type="password">` elements
2. **Locate Parent Form**: Find the nearest `<form>` tag containing the password input
3. **Find Related Elements**:
   - Username input: `input[type="text"]`, `input[type="email"]`, or inputs containing "user"/"login"/"email"
   - Submit button: `input[type="submit"]`, `button[type="submit"]`, or buttons containing "Login"/"Sign in"
4. **Extract HTML Snippet**: Return HTML code containing the complete authentication component
5. **Extract Metadata**: Get the form's `method` and `action` attributes

## Notes

- Some websites may have anti-scraping mechanisms that could block requests
- Dynamically loaded content (via JavaScript) may not be detectable
- Some websites may require login to access the login page
- Timeout is set to 10 seconds, large websites may need more time

## Development

### Running Both Servers

You can run both servers simultaneously:

**Terminal 1 (Backend):**
```bash
cd backend
python main.py
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

The frontend is configured to proxy API requests to the backend automatically.

### Building for Production

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm run build
npm run preview
```

## License

MIT License

## Author

AI Engineer Technical Assessment
