import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { User } from "lucide-react";

const CLERK_ENABLED = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

export function UserAvatar({ afterSignOutUrl = "/" }: { afterSignOutUrl?: string }) {
  const [ClerkUserButton, setClerkUserButton] = useState<React.ComponentType<{ afterSignOutUrl?: string }> | null>(null);

  useEffect(() => {
    if (CLERK_ENABLED) {
      import("@clerk/clerk-react").then((mod) => {
        setClerkUserButton(() => mod.UserButton);
      });
    }
  }, []);

  if (ClerkUserButton) {
    return <ClerkUserButton afterSignOutUrl={afterSignOutUrl} />;
  }

  return (
    <Button variant="ghost" size="icon">
      <User className="h-4 w-4" />
    </Button>
  );
}
