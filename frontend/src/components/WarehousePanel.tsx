/**
 * WarehousePanel - Shows warehouse connection status in sidebar
 *
 * Displays current MotherDuck connection with controls to
 * edit or disconnect the warehouse.
 */

import { Button } from '@/components/ui/button';
import { Database, Settings, X, AlertCircle } from 'lucide-react';
import { WarehouseStatus } from '@/hooks/use-warehouse';

interface WarehousePanelProps {
  warehouseStatus: WarehouseStatus;
  onConfigure: () => void;
  onDisconnect: () => void;
}

export function WarehousePanel({
  warehouseStatus,
  onConfigure,
  onDisconnect,
}: WarehousePanelProps) {
  const isConnected = warehouseStatus.connection_status === 'connected';
  const hasError = warehouseStatus.connection_status === 'error';

  if (!isConnected && !hasError) {
    // Not connected state
    return (
      <div className="p-4 border-t border-border">
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Database className="h-4 w-4" />
            <span className="text-sm font-medium">Warehouse</span>
          </div>
          <Button
            onClick={onConfigure}
            size="sm"
            className="w-full"
          >
            <Database className="h-4 w-4 mr-2" />
            Connect Warehouse
          </Button>
          <p className="text-xs text-muted-foreground">
            Connect your MotherDuck database to start analyzing data
          </p>
        </div>
      </div>
    );
  }

  // Connected state
  return (
    <div className="p-4 border-t border-border">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Warehouse</span>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between p-2 bg-accent/50 rounded-lg">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <div className={`h-2 w-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium truncate">
                  {warehouseStatus.warehouse_type === 'motherduck' ? 'MotherDuck' :
                   warehouseStatus.warehouse_type === 'bigquery' ? 'BigQuery' :
                   warehouseStatus.warehouse_type === 'snowflake' ? 'Snowflake' :
                   warehouseStatus.warehouse_type === 'postgresql' ? 'PostgreSQL' :
                   warehouseStatus.warehouse_type === 'redshift' ? 'Amazon Redshift' :
                   warehouseStatus.warehouse_type}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {warehouseStatus.database_name}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1 flex-shrink-0">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={onConfigure}
                title="Edit connection"
              >
                <Settings className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={onDisconnect}
                title="Disconnect"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          {hasError && (
            <div className="flex items-start gap-2 p-2 bg-red-50 dark:bg-red-950/20 rounded-lg border border-red-200 dark:border-red-900">
              <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-600">
                Connection error. Please check your credentials.
              </p>
            </div>
          )}

          {isConnected && warehouseStatus.connected_at && (
            <p className="text-xs text-muted-foreground">
              Connected {new Date(warehouseStatus.connected_at).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
