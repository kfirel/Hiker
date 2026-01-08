# Admin Dashboard - Frontend

React-based admin dashboard for the Hiker hitchhiking system.

## Development

### Prerequisites
- Node.js 18+ and npm

### Installation
```bash
npm install
```

### Running Dev Server
```bash
npm run dev
```
The dashboard will be available at http://localhost:3000/admin

The dev server is configured to proxy API calls to http://localhost:8080

### Building for Production
```bash
npm run build
```
This creates a `dist/` folder with optimized production files.

## Features

- 📊 **Dashboard**: Overview statistics, trends, and charts
- 👥 **Users Management**: View, search, and export users
- 🚗 **Rides Management**: View active rides and hitchhiker requests
- ⚠️ **Errors & Logs**: Monitor system errors and activity logs

## Tech Stack

- **React 18** - UI library
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Query** - Data fetching and caching
- **Recharts** - Charts and visualizations
- **React Router** - Navigation
- **Axios** - HTTP client

## Configuration

### API Token
The admin dashboard requires an admin token to access the API.
Set the token in localStorage:
```javascript
localStorage.setItem('admin_token', 'your-admin-token');
```

Or set the `ADMIN_TOKEN` environment variable in your backend `.env` file.

## Deployment

The frontend is automatically built and served by the FastAPI backend when deployed to Cloud Run.

For manual deployment:
1. Build: `npm run build`
2. The `dist/` folder is served by FastAPI at `/admin`



