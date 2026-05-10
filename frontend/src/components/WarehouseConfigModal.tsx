/**
 * WarehouseConfigModal - Modal for configuring warehouse connections
 *
 * Supports multiple warehouse types: MotherDuck, BigQuery, Snowflake, PostgreSQL.
 * Shows different form fields based on selected type.
 */

import { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Eye, EyeOff, Loader2 } from 'lucide-react';

const WAREHOUSE_TYPES = [
  { value: 'motherduck', label: 'MotherDuck' },
  { value: 'bigquery', label: 'BigQuery' },
  { value: 'snowflake', label: 'Snowflake' },
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'redshift', label: 'Amazon Redshift' },
] as const;

const REDSHIFT_AUTH_MODES = [
  { value: 'standard', label: 'Standard' },
  { value: 'iam', label: 'IAM' },
  { value: 'serverless', label: 'Serverless' },
] as const;

interface WarehouseConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfigure: (warehouseType: string, credentials: Record<string, string>) => Promise<any>;
  isLoading: boolean;
}

export function WarehouseConfigModal({
  isOpen,
  onClose,
  onConfigure,
  isLoading,
}: WarehouseConfigModalProps) {
  const [warehouseType, setWarehouseType] = useState('motherduck');
  const [redshiftAuthMode, setRedshiftAuthMode] = useState('standard');
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleCredentialChange = (field: string, value: string) => {
    setCredentials(prev => ({ ...prev, [field]: value }));
  };

  const toggleSecret = (field: string) => {
    setShowSecrets(prev => ({ ...prev, [field]: !prev[field] }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    // Add default ports
    const finalCredentials = { ...credentials };
    if (warehouseType === 'postgresql' && !finalCredentials.port) {
      finalCredentials.port = '5432';
    }
    if (warehouseType === 'redshift' && !finalCredentials.port) {
      finalCredentials.port = '5439';
    }

    try {
      await onConfigure(warehouseType, finalCredentials);
      setSuccess(true);
      setTimeout(() => {
        handleClose();
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to configure warehouse');
    }
  };

  const handleClose = () => {
    setWarehouseType('motherduck');
    setRedshiftAuthMode('standard');
    setCredentials({});
    setShowSecrets({});
    setError(null);
    setSuccess(false);
    onClose();
  };

  const renderSecretField = (id: string, label: string, placeholder: string) => (
    <div className="space-y-2" key={id}>
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={showSecrets[id] ? 'text' : 'password'}
          value={credentials[id] || ''}
          onChange={(e) => handleCredentialChange(id, e.target.value)}
          placeholder={placeholder}
          className="pr-10"
          disabled={isLoading}
        />
        <button
          type="button"
          onClick={() => toggleSecret(id)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
          disabled={isLoading}
        >
          {showSecrets[id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );

  const renderTextField = (id: string, label: string, placeholder: string, hint?: string) => (
    <div className="space-y-2" key={id}>
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="text"
        value={credentials[id] || ''}
        onChange={(e) => handleCredentialChange(id, e.target.value)}
        placeholder={placeholder}
        disabled={isLoading}
      />
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );

  const renderFields = () => {
    switch (warehouseType) {
      case 'motherduck':
        return (
          <>
            {renderSecretField('token', 'MotherDuck Token', 'Enter your MotherDuck access token')}
            <p className="text-xs text-muted-foreground">
              Get your token from{' '}
              <a href="https://app.motherduck.com/settings/keys" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">
                MotherDuck Settings
              </a>
            </p>
            {renderTextField('database', 'Database Name', "e.g., 'my_db' or 'md:' for shared database", 'Use "md:" for MotherDuck shared database, or specify your database name')}
          </>
        );
      case 'bigquery':
        return (
          <>
            {renderTextField('project_id', 'Project ID', 'my-gcp-project')}
            <div className="space-y-2">
              <Label htmlFor="credentials_json">Service Account JSON</Label>
              <textarea
                id="credentials_json"
                value={credentials.credentials_json || ''}
                onChange={(e) => handleCredentialChange('credentials_json', e.target.value)}
                placeholder="Paste your service account JSON here"
                className="w-full min-h-[100px] rounded-md border border-input bg-background px-3 py-2 text-sm"
                disabled={isLoading}
              />
            </div>
          </>
        );
      case 'snowflake':
        return (
          <>
            {renderTextField('account', 'Account', 'xy12345.us-east-1')}
            {renderTextField('username', 'Username', 'Enter username')}
            {renderSecretField('password', 'Password', 'Enter password')}
            {renderTextField('warehouse', 'Warehouse', 'COMPUTE_WH')}
            {renderTextField('database', 'Database', 'MY_DATABASE')}
          </>
        );
      case 'postgresql':
        return (
          <>
            {renderTextField('host', 'Host', 'localhost')}
            {renderTextField('port', 'Port', '5432', 'Default: 5432')}
            {renderTextField('database', 'Database', 'my_database')}
            {renderTextField('username', 'Username', 'Enter username')}
            {renderSecretField('password', 'Password', 'Enter password')}
          </>
        );
      case 'redshift':
        return (
          <>
            {/* Auth mode selector */}
            <div className="space-y-2">
              <Label>Authentication Mode</Label>
              <div className="grid grid-cols-3 gap-2">
                {REDSHIFT_AUTH_MODES.map((mode) => (
                  <button
                    key={mode.value}
                    type="button"
                    onClick={() => {
                      setRedshiftAuthMode(mode.value);
                      setCredentials({});
                      setShowSecrets({});
                    }}
                    className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                      redshiftAuthMode === mode.value
                        ? 'border-primary bg-primary/10 text-primary font-medium'
                        : 'border-border hover:border-primary/50'
                    }`}
                    disabled={isLoading}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
            </div>
            {/* Auth-mode-specific fields */}
            {redshiftAuthMode === 'standard' && (
              <>
                {renderTextField('host', 'Host', 'my-cluster.xxxx.us-east-1.redshift.amazonaws.com')}
                {renderTextField('port', 'Port', '5439', 'Default: 5439')}
                {renderTextField('database', 'Database', 'dev')}
                {renderTextField('username', 'Username', 'Enter username')}
                {renderSecretField('password', 'Password', 'Enter password')}
              </>
            )}
            {redshiftAuthMode === 'iam' && (
              <>
                {renderTextField('cluster_identifier', 'Cluster Identifier', 'my-redshift-cluster')}
                {renderTextField('database', 'Database', 'dev')}
                {renderTextField('db_user', 'Database User', 'admin')}
                {renderSecretField('access_key', 'AWS Access Key ID', 'AKIA...')}
                {renderSecretField('secret_key', 'AWS Secret Access Key', 'Enter secret key')}
                {renderTextField('region', 'Region', 'us-east-1', 'Default: us-east-1')}
              </>
            )}
            {redshiftAuthMode === 'serverless' && (
              <>
                {renderTextField('workgroup', 'Workgroup Name', 'default')}
                {renderTextField('database', 'Database', 'dev')}
                {renderSecretField('access_key', 'AWS Access Key ID', 'AKIA...')}
                {renderSecretField('secret_key', 'AWS Secret Access Key', 'Enter secret key')}
                {renderTextField('region', 'Region', 'us-east-1', 'Default: us-east-1')}
              </>
            )}
          </>
        );
      default:
        return null;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Configure Warehouse</DialogTitle>
          <DialogDescription>
            Connect your data warehouse to start analyzing your data.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          {/* Warehouse Type Selector */}
          <div className="space-y-2">
            <Label>Warehouse Type</Label>
            <div className="grid grid-cols-2 gap-2">
              {WAREHOUSE_TYPES.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => {
                    setWarehouseType(type.value);
                    setCredentials({});
                    setShowSecrets({});
                    setError(null);
                  }}
                  className={`px-3 py-2 text-sm rounded-md border transition-colors ${
                    warehouseType === type.value
                      ? 'border-primary bg-primary/10 text-primary font-medium'
                      : 'border-border hover:border-primary/50'
                  }`}
                  disabled={isLoading}
                >
                  {type.label}
                </button>
              ))}
            </div>
          </div>

          {/* Dynamic Fields */}
          {renderFields()}

          {/* Error/Success Messages */}
          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 dark:bg-red-950/50 rounded-lg border border-red-200 dark:border-red-900">
              {error}
            </div>
          )}

          {success && (
            <div className="p-3 text-sm text-green-600 bg-green-50 dark:bg-green-950/50 rounded-lg border border-green-200 dark:border-green-900">
              Connected successfully! Redirecting...
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading || success}>
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Testing Connection...
                </>
              ) : success ? (
                'Connected!'
              ) : (
                'Connect'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
