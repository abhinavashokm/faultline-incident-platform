"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Mail, ArrowLeft, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

import { AuthShell } from "@/components/layout/auth-shell";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useVerifyEmail, useResendOtp } from "@/features/auth/hooks";

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const emailParam = searchParams.get("email") || "elena@faultline.io";

  const [otp, setOtp] = useState<string[]>(["", "", "", "", "", ""]);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState<number>(30);

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const { mutate: verifyOtp, isPending } = useVerifyEmail(emailParam);
  const { mutate: resendOtp, isPending: isResending } = useResendOtp();

  // Mask email for display
  const maskedEmail = React.useMemo(() => {
    const parts = emailParam.split("@");
    if (parts.length !== 2) return emailParam;
    const [user, domain] = parts;
    const maskedUser =
      user.length > 2
        ? `${user[0]}${"*".repeat(user.length - 2)}${user[user.length - 1]}`
        : `${user}***`;
    return `${maskedUser}@${domain}`;
  }, [emailParam]);

  // Auto-focus first input on mount
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  // Cooldown countdown
  useEffect(() => {
    if (cooldown <= 0) return;
    const interval = setInterval(() => {
      setCooldown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldown]);

  const handleChange = (index: number, val: string) => {
    const cleanVal = val.replace(/\D/g, "");
    if (!cleanVal && val !== "") return;

    const newOtp = [...otp];
    newOtp[index] = cleanVal.slice(-1);
    setOtp(newOtp);
    setFormError(null);

    if (cleanVal && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace") {
      if (!otp[index] && index > 0) {
        inputRefs.current[index - 1]?.focus();
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").trim().replace(/\D/g, "");
    if (!pastedData) return;

    const digits = pastedData.slice(0, 6).split("");
    const newOtp = [...otp];
    digits.forEach((d, i) => {
      newOtp[i] = d;
    });
    setOtp(newOtp);
    setFormError(null);

    const nextFocusIndex = Math.min(digits.length, 5);
    inputRefs.current[nextFocusIndex]?.focus();
  };

  const handleVerify = () => {
    const code = otp.join("");
    if (code.length !== 6) {
      setFormError("Please enter all 6 digits of the verification code.");
      return;
    }

    setFormError(null);
    verifyOtp(
      { code },
      {
        onSuccess: () => {
          setSuccessMsg("Email successfully verified! Redirecting to project onboarding...");
          setTimeout(() => {
            router.push("/onboarding/create-project");
          }, 800);
        },
        onError: (err: any) => {
          setFormError(
            err.message || "Invalid or expired verification code. Please check and try again."
          );
        },
      }
    );
  };

  const handleResend = () => {
    if (cooldown > 0 || isResending) return;
    setFormError(null);
    setSuccessMsg(null);

    resendOtp(emailParam, {
      onSuccess: () => {
        setCooldown(30);
        setSuccessMsg("A new verification code has been dispatched to your email.");
      },
      onError: (err: any) => {
        setFormError(err.message || "Failed to resend code. Please try again.");
      },
    });
  };

  return (
    <AuthShell
      title="Verify your email"
      subtitle={`We've sent a 6-digit verification code to ${maskedEmail}`}
      footerContent={
        <Link
          href="/signup"
          className="inline-flex items-center gap-1.5 text-body-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Use a different email address</span>
        </Link>
      }
    >
      <div className="flex flex-col items-center">
        <div className="w-12 h-12 rounded-full bg-primary-tint border border-primary-subdued flex items-center justify-center text-primary mb-6">
          <Mail className="h-6 w-6" />
        </div>

        {formError && (
          <Alert variant="destructive" className="mb-5 text-left">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle className="text-body-sm font-semibold">Verification Error</AlertTitle>
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}

        {successMsg && (
          <Alert variant="success" className="mb-5 text-left">
            <CheckCircle2 className="h-4 w-4" />
            <AlertTitle className="text-body-sm font-semibold">Success</AlertTitle>
            <AlertDescription>{successMsg}</AlertDescription>
          </Alert>
        )}

        <div className="flex items-center justify-center gap-2 sm:gap-2.5 my-3">
          {otp.map((digit, idx) => (
            <input
              key={idx}
              ref={(el) => {
                inputRefs.current[idx] = el;
              }}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleChange(idx, e.target.value)}
              onKeyDown={(e) => handleKeyDown(idx, e)}
              onPaste={handlePaste}
              disabled={isPending}
              className="w-11 h-12 sm:w-12 sm:h-12 rounded-md border border-border bg-card text-center font-mono text-[20px] font-semibold text-text-primary shadow-level-1 focus:border-primary focus:ring-2 focus:ring-primary-subdued focus:outline-none transition-all"
            />
          ))}
        </div>

        <p className="font-mono text-[11px] text-text-muted mt-2 mb-5">
          Tip: Enter any 6 digits (e.g. 123456). Use 999999 to test expired, 000000 for invalid.
        </p>

        <Button
          onClick={handleVerify}
          className="w-full h-10 gap-2 mb-4"
          disabled={isPending || otp.join("").length !== 6}
        >
          {isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Verifying code...</span>
            </>
          ) : (
            <span>Verify email</span>
          )}
        </Button>

        <div className="flex items-center gap-2 text-body-sm text-text-secondary">
          <span>Didn&apos;t receive the code?</span>
          {cooldown > 0 ? (
            <span className="font-mono text-[12px] text-text-muted font-medium">
              Resend in {cooldown}s
            </span>
          ) : (
            <button
              type="button"
              onClick={handleResend}
              disabled={isResending}
              className="font-medium text-primary hover:underline focus:outline-none"
            >
              Resend code
            </button>
          )}
        </div>
      </div>
    </AuthShell>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-canvas">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
