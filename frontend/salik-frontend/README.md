# StrategAI - Frontend

AI-powered E-commerce Profit Optimization Tool

## 🚀 Features

- **Product Search**: Search for products and get comprehensive market analysis
- **Wholesale Analysis**: View supplier details, MOQ, unit prices, and lead times
- **Retail Market Insights**: Analyze competitor pricing across multiple platforms
- **Profit Optimization**: Calculate profit margins and get recommendations
- **Data Analytics**: Interactive charts and visualizations
- **Strategic Recommendations**: AI-powered suggestions for optimal business decisions
- **Comprehensive Reports**: Download detailed analysis reports

## 🛠️ Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **React Router** - Navigation
- **TanStack Query** - Data fetching and caching
- **Axios** - HTTP client
- **Recharts** - Data visualization
- **Lucide Icons** - Icon library

## 📦 Installation

1. Clone the repository:
```bash
git clone <repository-url>
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

The application will be available at `http://localhost:5173`

## 🔧 Configuration

### API Endpoint

The default API endpoint is set to `http://localhost:8000`. You can modify this in `src/services/api.ts`:

```typescript
const API_BASE_URL = 'http://localhost:8000';
```

## 📝 Usage

1. **Dashboard**: Enter a product name and click search
2. **Results**: View wholesale suppliers and retail market data
3. **Analytics**: See detailed analytics and metrics
4. **Strategy**: Get AI-powered recommendations
5. **Visualization**: Explore interactive charts
6. **Reports**: Download comprehensive reports

## 🏗️ Project Structure

```
src/
├── components/          # Reusable components
│   ├── ui/             # UI primitives (Button, Card, etc.)
│   ├── Navbar.tsx
│   ├── Footer.tsx
│   ├── SearchBar.tsx
│   ├── WholesaleCard.tsx
│   ├── RetailCard.tsx
│   ├── ComparisonSummary.tsx
│   ├── LoaderSkeleton.tsx
│   └── ErrorAlert.tsx
├── pages/              # Page components
│   ├── Dashboard.tsx
│   ├── Results.tsx
│   ├── Analytics.tsx
│   ├── Strategy.tsx
│   ├── Visualization.tsx
│   └── Reports.tsx
├── services/           # API services
│   └── api.ts
├── hooks/              # Custom hooks
│   └── useScraper.ts
├── types/              # TypeScript types
│   └── index.ts
├── utils/              # Utility functions
│   ├── comparison.ts
│   └── utils.ts
├── App.tsx
└── main.tsx
```

## 🎨 Styling

The project uses TailwindCSS with a custom color scheme inspired by purple and blue gradients. The design follows modern SaaS product patterns similar to Stripe and Notion.

## 📊 API Integration

The frontend expects the following API response structure:

```typescript
{
  product_name: string;
  links_used: { [key: string]: string };
  wholesale: {
    made_in_china: WholesaleItem[];
  };
  retail: RetailItem[];
}
```

## 🚢 Build for Production

```bash
npm run build
```

The build output will be in the `dist` directory.

## 🌐 Deployment

### Vercel

1. Install Vercel CLI: `npm i -g vercel`
2. Run: `vercel`

### Netlify

1. Install Netlify CLI: `npm i -g netlify-cli`
2. Run: `netlify deploy --prod`

## 📄 License

MIT

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

