import { useState, FormEvent } from 'react';
import { Search, Loader2 } from 'lucide-react';
import Input from './ui/Input';
import Button from './ui/Button';

interface SearchBarProps {
  onSearch: (productName: string, category: string) => void;
  isLoading?: boolean;
}

export default function SearchBar({ onSearch, isLoading = false }: SearchBarProps) {
  const [productName, setProductName] = useState('');
  const [category, setCategory] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (productName.trim() && !isLoading) {
      onSearch(productName.trim(), category.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
      <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-2 shadow-[0_20px_60px_rgba(2,6,23,0.25)] backdrop-blur-2xl">
        <div className="flex gap-2">
          <div className="flex-1 relative flex">
            <Search className="absolute left-3 top-1/2 z-10 h-5 w-5 -translate-y-1/2 text-gray-500" />
            <Input
              type="text"
              placeholder="Category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="h-12 w-1/3 rounded-r-none border-r-0 pl-10 text-base focus:z-10"
              disabled={isLoading}
            />
            <Input
              type="text"
              placeholder="Enter product name (e.g., HyperX Cloud III)"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              className="h-12 w-2/3 rounded-l-none border-l-0 pl-4 text-base focus:z-10"
              disabled={isLoading}
            />
          </div>
          <Button
            type="submit"
            disabled={isLoading || !productName.trim()}
            size="lg"
            className="px-8"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="mr-2 h-4 w-4" />
                Search
              </>
            )}
          </Button>
        </div>
      </div>
    </form>
  );
}


