import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authService } from "@/api/auth";
import { toast } from "sonner";
import { LayoutDashboard } from "lucide-react";

export function LoginPage() {
  const [employeeId, setEmployeeId] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  // OTP challenge state (when the account has OTP login enabled).
  const [step, setStep] = useState<"credentials" | "otp">("credentials");
  const [otp, setOtp] = useState("");
  const [otpUserId, setOtpUserId] = useState("");
  const [phoneHint, setPhoneHint] = useState("");

  const completeLogin = (data: any) => {
    toast.success("Login successful!");
    navigate(data?.user?.mustChangePassword ? "/change-password" : "/");
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeId || !password) {
      toast.error("Please enter both Employee ID and password");
      return;
    }

    setIsLoading(true);
    try {
      const data = await authService.login(employeeId, password);
      if (data?.otp_required) {
        // OTP enabled — move to the verification step instead of logging in.
        setOtpUserId(data.user_id || employeeId);
        setPhoneHint(data.phone_hint || "");
        setOtp("");
        setStep("otp");
        toast.success(data.detail || "An OTP has been sent to your registered phone.");
      } else {
        completeLogin(data);
      }
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail || "Login failed. Please check your credentials."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otp.trim()) {
      toast.error("Please enter the OTP code");
      return;
    }
    setIsLoading(true);
    try {
      const data = await authService.verifyOtp(otpUserId, otp.trim());
      completeLogin(data);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Invalid or expired OTP. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setIsLoading(true);
    try {
      await authService.resendOtp(otpUserId);
      toast.success("A new OTP has been sent to your phone.");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Could not resend OTP. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-sm border p-8">
        <div className="flex flex-col items-center mb-8">
          <div className="bg-primary text-primary-foreground p-3 rounded-xl mb-4 shadow-sm">
            <LayoutDashboard size={28} />
          </div>
          <h1 className="text-2xl font-bold text-foreground">
            {step === "otp" ? "Enter Verification Code" : "Welcome Back"}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {step === "otp"
              ? `We sent a code to ${phoneHint || "your registered phone"}`
              : "Sign in to Committee Manager"}
          </p>
        </div>

        {step === "credentials" ? (
          <>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="employeeId">Employee ID</Label>
                <Input
                  id="employeeId"
                  type="text"
                  placeholder="e.g. admin123"
                  value={employeeId}
                  onChange={(e) => setEmployeeId(e.target.value)}
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>
              <Button
                type="submit"
                className="w-full bg-primary hover:bg-primary/90 mt-6"
                disabled={isLoading}
              >
                {isLoading ? "Signing in..." : "Sign In"}
              </Button>
            </form>

            <p className="text-center text-sm text-muted-foreground mt-6">
              Don't have an account?{" "}
              <Link to="/signup" className="font-medium text-primary hover:underline">
                Sign up
              </Link>
            </p>
          </>
        ) : (
          <form onSubmit={handleVerifyOtp} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="otp">Verification Code</Label>
              <Input
                id="otp"
                type="text"
                inputMode="numeric"
                autoFocus
                placeholder="Enter the 6-digit code"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 mt-2"
              disabled={isLoading}
            >
              {isLoading ? "Verifying..." : "Verify & Sign In"}
            </Button>
            <div className="flex items-center justify-between text-sm">
              <button
                type="button"
                onClick={() => {
                  setStep("credentials");
                  setOtp("");
                }}
                className="font-medium text-muted-foreground hover:underline"
                disabled={isLoading}
              >
                ← Back
              </button>
              <button
                type="button"
                onClick={handleResendOtp}
                className="font-medium text-primary hover:underline disabled:opacity-50"
                disabled={isLoading}
              >
                Resend code
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
