import { ExternalLink, ShoppingBag } from 'lucide-react';
import { RetailItem } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import Badge from './ui/Badge';
import Button from './ui/Button';

interface RetailCardProps {
  item: RetailItem;
}

export default function RetailCard({ item }: RetailCardProps) {
  return (
    <Card className="border-white/10">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="mb-2 line-clamp-2 text-lg">{item.title}</CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{item.platform}</Badge>
              {item.promo && (
                <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-300">
                  {item.promo}
                </Badge>
              )}
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] p-3">
          <ShoppingBag className="h-4 w-4 text-cyan-300" />
          <div>
            <p className="text-xs text-gray-400">Seller</p>
            <p className="font-semibold">{item.seller}</p>
          </div>
        </div>
        <div>
          <p className="mb-1 text-xs text-gray-400">List Price</p>
          <p className="text-2xl font-bold text-cyan-300">
            {item.list_price.toLocaleString()} PKR
          </p>
        </div>
        {item.url && (
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => window.open(item.url, '_blank')}
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            View Listing
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

