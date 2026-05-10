import { SignUp, useAuth } from "@clerk/clerk-react";
import { Link, Navigate } from "react-router-dom";

export default function SignUpPage() {
  const { isSignedIn, isLoaded } = useAuth();

  if (isLoaded && isSignedIn) {
    return <Navigate to="/chat" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background p-4">
      <Link to="/" className="flex items-center gap-2 mb-8">
        <span className="font-semibold text-xl text-foreground">datachat</span>
      </Link>
      <SignUp
        signInUrl="/sign-in"
        forceRedirectUrl="/chat"
      />
    </div>
  );
}
