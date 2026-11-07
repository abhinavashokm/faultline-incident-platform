"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, AlertCircle, ArrowRight, Loader2, Check } from "lucide-react";

import { AuthShell } from "@/components/layout/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { signupSchema, SignupFormData } from "@/features/auth/schemas";
import { useSignup } from "@/features/auth/hooks";
import { AuthErrorAlert } from "@/features/auth/components/auth-error-alert";

export default function SignupPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      confirmPassword: "",
    },
    mode: "onChange",
  });

  const { mutate: signup, isPending } = useSignup();
  const passwordValue = form.watch("password") || "";

  // Password criteria indicators
  const hasLength = passwordValue.length >= 8;
  const hasUpper = /[A-Z]/.test(passwordValue);
  const hasNumber = /[0-9]/.test(passwordValue);

  function onSubmit(values: SignupFormData) {
    setFormError(null);

    signup(values, {
      onSuccess: () => {
        router.push(`/verify-email?email=${encodeURIComponent(values.email)}`);
      },
      onError: (err: any) => {
        setFormError(
          err.message || "Could not complete account creation. Please try again."
        );
      },
    });
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start monitoring system telemetry and real-time metrics."
      footerContent={
        <p>
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-primary hover:underline"
          >
            Log in
          </Link>
        </p>
      }
    >
      <AuthErrorAlert error={formError} />

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Full name</FormLabel>
                <FormControl>
                  <Input
                    placeholder="Elena Vance"
                    autoComplete="name"
                    disabled={isPending}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-center justify-between">
                  <FormLabel>Work email</FormLabel>
                  <span className="font-mono text-[11px] text-text-muted">RFC 5322</span>
                </div>
                <FormControl>
                  <Input
                    type="email"
                    placeholder="elena@company.com"
                    autoComplete="email"
                    disabled={isPending}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Password</FormLabel>
                <div className="relative">
                  <FormControl>
                    <Input
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      disabled={isPending}
                      className="pr-10"
                      {...field}
                    />
                  </FormControl>
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors focus:outline-none"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <FormMessage />

                {/* Password Strength Hints */}
                {passwordValue.length > 0 && (
                  <div className="mt-2 space-y-1 rounded bg-canvas border border-border p-2.5 text-label-sm">
                    <span className="text-text-muted text-[11px] font-medium block mb-1">
                      Password Requirements:
                    </span>
                    <div className="flex items-center gap-2">
                      <span
                        className={`h-3 w-3 rounded-full flex items-center justify-center ${
                          hasLength ? "bg-success text-card" : "bg-border text-text-muted"
                        }`}
                      >
                        <Check className="h-2 w-2" />
                      </span>
                      <span className={hasLength ? "text-text-primary" : "text-text-muted"}>
                        At least 8 characters
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`h-3 w-3 rounded-full flex items-center justify-center ${
                          hasUpper ? "bg-success text-card" : "bg-border text-text-muted"
                        }`}
                      >
                        <Check className="h-2 w-2" />
                      </span>
                      <span className={hasUpper ? "text-text-primary" : "text-text-muted"}>
                        At least one uppercase letter
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`h-3 w-3 rounded-full flex items-center justify-center ${
                          hasNumber ? "bg-success text-card" : "bg-border text-text-muted"
                        }`}
                      >
                        <Check className="h-2 w-2" />
                      </span>
                      <span className={hasNumber ? "text-text-primary" : "text-text-muted"}>
                        At least one number
                      </span>
                    </div>
                  </div>
                )}
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="confirmPassword"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Confirm password</FormLabel>
                <div className="relative">
                  <FormControl>
                    <Input
                      type={showConfirmPassword ? "text" : "password"}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      disabled={isPending}
                      className="pr-10"
                      {...field}
                    />
                  </FormControl>
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors focus:outline-none"
                    aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button
            type="submit"
            className="w-full h-10 gap-2 mt-2"
            disabled={isPending}
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Creating account...</span>
              </>
            ) : (
              <>
                <span>Create account</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </form>
      </Form>
    </AuthShell>
  );
}

