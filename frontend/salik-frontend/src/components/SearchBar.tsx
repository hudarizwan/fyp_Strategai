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
    <form onSubmit={handleSubmit} className="w-full max-w-4xl mx-auto">
      <div className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-2 shadow-[0_20px_60px_rgba(2,6,23,0.28)] backdrop-blur-2xl">
        <div className="flex gap-2 max-md:flex-col">
          <div className="relative flex w-full gap-2 max-md:flex-col">
            <div className="relative w-[28%] min-w-[9rem] max-md:w-full">
              <Search className="pointer-events-none absolute left-4 top-1/2 z-10 h-5 w-5 -translate-y-1/2 text-slate-500 max-md:top-4" />
              <Input
                type="text"
                placeholder="Category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="h-12 w-full rounded-r-none border-r-0 pl-11 text-base max-md:rounded-2xl max-md:border-r"
                disabled={isLoading}
              />
            </div>
            <div className="relative flex-1 max-md:w-full">
              <Input
                type="text"
                placeholder="Enter product name (e.g., HyperX Cloud III)"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                className="h-12 w-full rounded-l-none border-l-0 pl-4 text-base max-md:rounded-2xl max-md:border-l"
                disabled={isLoading}
              />
            </div>
          </div>
          <Button type="submit" disabled={isLoading || !productName.trim()} size="lg" className="px-8 max-md:w-full">
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
