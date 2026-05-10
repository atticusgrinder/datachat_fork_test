import { SignIn } from "@clerk/clerk-react";
import { Link } from "react-router-dom";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background p-4">
      <Link to="/" className="flex items-center gap-2 mb-8">
        <span className="font-semibold text-xl text-foreground">datachat</span>
      </Link>
      <SignIn
        signUpUrl="/sign-up"
        forceRedirectUrl="/chat"
      />
    </div>
  );
}
