export default function Footer() {
  return (
    <footer className="border-t border-white/10 bg-slate-950/90 backdrop-blur-xl">
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col items-center justify-between md:flex-row">
          <div className="mb-4 flex items-center space-x-2 md:mb-0">
            <span className="text-sm text-gray-400">
              © 2024 StrategAI. All rights reserved.
            </span>
          </div>
          <div className="text-sm text-gray-400">
            E-commerce Profit Optimization Platform
          </div>
        </div>
      </div>
    </footer>
  );
}
