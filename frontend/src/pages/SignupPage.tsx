import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authService } from "@/api/auth";
import { toast } from "sonner";
import { UserPlus } from "lucide-react";

export function SignupPage() {
  const [employeeId, setEmployeeId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sentHint, setSentHint] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeId.trim()) {
      toast.error("Please enter your Employee ID");
      return;
    }

    setIsLoading(true);
    try {
      const data = await authService.signup(employeeId.trim());
      setSentHint(data?.phone_hint || null);
      toast.success("A temporary password has been sent to your phone.");
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail || "Signup failed. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-sm border p-8">
        <div className="flex flex-col items-center mb-8">
          <div className="bg-primary text-primary-foreground p-3 rounded-xl mb-4 shadow-sm">
            <UserPlus size={28} />
          </div>
          <h1 className="text-2xl font-bold text-foreground">Create your account</h1>
          <p className="text-muted-foreground text-sm mt-1 text-center">
            Enter your Employee ID. We'll text a temporary password to your registered phone.
          </p>
        </div>

        {sentHint !== null ? (
          <div className="space-y-4 text-center">
            <div className="rounded-md border bg-green-50 p-4 text-sm text-green-800">
              A temporary password has been sent to your phone
              {sentHint ? ` (${sentHint})` : ""}. Use it to log in, then set a new
              password.
            </div>
            <Button className="w-full" onClick={() => navigate("/login")}>
              Go to Login
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSignup} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="employeeId">Employee ID</Label>
              <Input
                id="employeeId"
                type="text"
                placeholder="e.g. 1234"
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 mt-6"
              disabled={isLoading}
            >
              {isLoading ? "Sending..." : "Send Password"}
            </Button>
          </form>
        )}

        <p className="text-center text-sm text-muted-foreground mt-6">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
