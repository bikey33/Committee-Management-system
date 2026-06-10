import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authService } from "@/api/auth";
import { toast } from "sonner";
import { UserPlus } from "lucide-react";

export function SignupPage() {
  const navigate = useNavigate();

  const [step, setStep] = useState<"employee" | "verify">("employee");
  const [employeeId, setEmployeeId] = useState("");
  const [phoneHint, setPhoneHint] = useState("");
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const requestOtp = async () => {
    const data = await authService.signup(employeeId.trim());
    setPhoneHint(data?.phone_hint || "");
    setStep("verify");
    setOtp("");
    toast.success(data?.detail || "A verification code has been sent to your phone.");
  };

  const handleRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeId.trim()) {
      toast.error("Please enter your Employee ID");
      return;
    }
    setIsLoading(true);
    try {
      await requestOtp();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Signup failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    setIsLoading(true);
    try {
      await requestOtp();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Could not resend the code.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otp.trim()) {
      toast.error("Please enter the verification code");
      return;
    }
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }
    setIsLoading(true);
    try {
      await authService.signupVerify(employeeId.trim(), otp.trim(), password);
      toast.success("Account created! Please log in with your new password.");
      navigate("/login");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Verification failed. Please try again.");
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
          <h1 className="text-2xl font-bold text-foreground">
            {step === "employee" ? "Create your account" : "Verify & set password"}
          </h1>
          <p className="text-muted-foreground text-sm mt-1 text-center">
            {step === "employee"
              ? "Enter your Employee ID. We'll send a verification code to your registered phone."
              : `Enter the code sent to ${phoneHint || "your phone"} and choose a password.`}
          </p>
        </div>

        {step === "employee" ? (
          <form onSubmit={handleRequest} className="space-y-4">
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
              {isLoading ? "Sending code..." : "Send Verification Code"}
            </Button>
          </form>
        ) : (
          <form onSubmit={handleVerify} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="otp">Verification Code</Label>
              <Input
                id="otp"
                type="text"
                inputMode="numeric"
                autoFocus
                placeholder="Enter the code"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">New Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Re-enter your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 mt-2"
              disabled={isLoading}
            >
              {isLoading ? "Creating account..." : "Create Account"}
            </Button>
            <div className="flex items-center justify-between text-sm">
              <button
                type="button"
                onClick={() => setStep("employee")}
                className="font-medium text-muted-foreground hover:underline cursor-pointer"
                disabled={isLoading}
              >
                ← Back
              </button>
              <button
                type="button"
                onClick={handleResend}
                className="font-medium text-primary hover:underline cursor-pointer disabled:opacity-50"
                disabled={isLoading}
              >
                Resend code
              </button>
            </div>
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
