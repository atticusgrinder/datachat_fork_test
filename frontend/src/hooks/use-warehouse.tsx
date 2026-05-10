/**
 * useWarehouse - Warehouse connection state management
 *
 * Manages MotherDuck warehouse configuration and connection status.
 * Provides methods to configure, disconnect, and check warehouse status.
 */

import { useState, useEffect } from 'react';

export interface WarehouseStatus {
  warehouse_type: string | null;
  database_name: string | null;
  connection_status: 'connected' | 'disconnected' | 'error';
  connected_at: string | null;
}

export function useWarehouse() {
  const [warehouseStatus, setWarehouseStatus] = useState<WarehouseStatus>({
    warehouse_type: null,
    database_name: null,
    connection_status: 'disconnected',
    connected_at: null,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get access token from URL params (for shared access)
  const [accessToken] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('token');
  });

  const buildApiUrl = (endpoint: string) => {
    const baseUrl = `${import.meta.env.VITE_API_URL}${endpoint}`;
    return accessToken ? `${baseUrl}?token=${accessToken}` : baseUrl;
  };

  const fetchWarehouseStatus = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(buildApiUrl('/warehouse/status'));
      const data = await response.json();

      setWarehouseStatus(data);
    } catch (err) {
      console.error('Error fetching warehouse status:', err);
      setError('Failed to fetch warehouse status');
    } finally {
      setIsLoading(false);
    }
  };

  const configureWarehouse = async (token: string, database: string) => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(buildApiUrl('/warehouse/configure'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          motherduck_token: token,
          motherduck_database: database,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to configure warehouse');
      }

      if (data.success) {
        await fetchWarehouseStatus();
        return { success: true, databases: data.databases_found };
      } else {
        throw new Error('Configuration failed');
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to configure warehouse';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const disconnectWarehouse = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(buildApiUrl('/warehouse/disconnect'), {
        method: 'DELETE',
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to disconnect warehouse');
      }

      if (data.success) {
        await fetchWarehouseStatus();
        return { success: true };
      } else {
        throw new Error('Disconnection failed');
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to disconnect warehouse';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch status on mount
  useEffect(() => {
    fetchWarehouseStatus();
  }, []);

  return {
    warehouseStatus,
    isLoading,
    error,
    configureWarehouse,
    disconnectWarehouse,
    refreshStatus: fetchWarehouseStatus,
  };
}
