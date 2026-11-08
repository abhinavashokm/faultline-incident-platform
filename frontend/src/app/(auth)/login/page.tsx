"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, AlertCircle, ArrowRight, Loader2, Info } from "lucide-react";

import { AuthShell } from "@/components/layout/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { loginSchema, LoginFormData } from "@/features/auth/schemas";
import { useLogin } from "@/features/auth/hooks";
import { AuthErrorAlert } from "@/features/auth/components/auth-error-alert";
import { useAuth } from "@/features/auth/auth-context";
import { listProjectsApi } from "@/features/projects/api";

export default function LoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [resetSent, setResetSent] = useState(false);

  const isDev = process.env.NODE_ENV === "development";

  const form = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: isDev ? "developer3@example.com" : "",
      password: isDev ? "passwordA1" : "",
      remember: false,
    },
  });

  const { mutate: login, isPending } = useLogin();
  const { onLoginSuccess } = useAuth();

  function onSubmit(values: LoginFormData) {
    setFormError(null);
    setResetSent(false);

    login(values, {
      onSuccess: async (data) => {
        onLoginSuccess();
        const slug = data.workspace?.slug || "overview";
        try {
          const projects = await listProjectsApi();
          if (projects.length === 0) {
            router.push("/onboarding/create-project");
          } else {
            router.push(`/${slug}/overview`);
          }
        } catch {
          // If the project list fetch fails, fall back to the dashboard;
          // the layout guard will re-check and redirect if still needed.
          router.push(`/${slug}/overview`);
        }
      },
      onError: (err: any) => {
        if (err.message === "email_not_verified" || err.details?.detail === "email_not_verified" || err.details?.unverified) {
          router.push(`/verify-email?email=${encodeURIComponent(values.email)}`);
          return;
        }
        console.log(err.message)
        setFormError(
          err.message || "Invalid credentials. Please verify your email and password."
        );
      },
    });
  }

  const handleForgotPassword = () => {
    setFormError(null);
    setResetSent(true);
  };

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to continue monitoring your applications."
      footerContent={
        <p>
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="font-medium text-primary hover:underline"
          >
            Sign up
          </Link>
        </p>
      }
    >
      <AuthErrorAlert error={formError} />

      {resetSent && (
        <Alert variant="info" className="mb-4">
          <Info className="h-4 w-4" />
          <AlertTitle className="text-body-sm font-semibold">Password Reset Dispatched</AlertTitle>
          <AlertDescription>
            If an account exists for this email, password recovery instructions have been sent.
          </AlertDescription>
        </Alert>
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-center justify-between">
                  <FormLabel>Work email</FormLabel>
                </div>
                <FormControl>
                  <Input
                    type="email"
                    placeholder="name@company.com"
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
                      autoComplete="current-password"
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
              </FormItem>
            )}
          />

          <div className="flex items-center justify-between pt-0.5">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-border text-primary focus:ring-primary focus:ring-offset-0"
                {...form.register("remember")}
              />
              <span className="text-body-sm text-text-secondary">
                Remember this device
              </span>
            </label>

            <button
              type="button"
              onClick={handleForgotPassword}
              className="text-label-md font-medium text-primary hover:underline focus:outline-none"
            >
              Forgot password?
            </button>
          </div>

          <Button
            type="submit"
            className="w-full h-10 gap-2 mt-2"
            disabled={isPending}
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Signing in...</span>
              </>
            ) : (
              <>
                <span>Log in</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </form>
      </Form>
    </AuthShell>
  );
}

