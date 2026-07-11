import { useState } from 'react';
import { ExternalLink, ChevronDown, ChevronUp, Package, DollarSign, Clock, MapPin } from 'lucide-react';
import { WholesaleItem } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import Badge from './ui/Badge';
import Button from './ui/Button';

interface WholesaleCardProps {
  item: WholesaleItem;
  linkUrl?: string;
}

export default function WholesaleCard({ item, linkUrl }: WholesaleCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <Card className="border-white/10">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="mb-2 text-lg">{item.supplier}</CardTitle>
            <div className="mb-2 flex items-center gap-2">
              <Badge variant="outline">{item.platform}</Badge>
              <Badge variant="secondary">{item.origin}</Badge>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <Package className="h-4 w-4 text-cyan-300" />
            <div>
              <p className="text-xs text-gray-400">MOQ</p>
              <p className="font-semibold">{item.moq.toLocaleString()} pcs</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <DollarSign className="h-4 w-4 text-indigo-300" />
            <div>
              <p className="text-xs text-gray-400">Unit Price</p>
              <p className="font-semibold">
                ${item.unit_price.toFixed(2)} / {item.unit_price_pkr.toLocaleString()} PKR
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <Clock className="h-4 w-4 text-cyan-300" />
            <div>
              <p className="text-xs text-gray-400">Lead Time</p>
              <p className="font-semibold">{item.lead_time || 'N/A'}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <MapPin className="h-4 w-4 text-indigo-300" />
            <div>
              <p className="text-xs text-gray-400">Origin</p>
              <p className="font-semibold">{item.origin}</p>
            </div>
          </div>
        </div>

        {Object.keys(item.attributes_listing).length > 0 && (
          <div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
              className="w-full justify-between rounded-xl border border-white/10 bg-white/[0.03]"
              >
                <span>View Attributes</span>
                {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            {isExpanded && (
              <div className="mt-2 space-y-2 rounded-xl border border-white/10 bg-white/[0.03] p-3">
                {Object.entries(item.attributes_listing).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="text-gray-400">{key}:</span>
                    <span className="font-medium">{String(value)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {linkUrl && (
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => window.open(linkUrl, '_blank')}
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            View Product Page
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

