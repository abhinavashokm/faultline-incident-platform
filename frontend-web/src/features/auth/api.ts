import { delay, ApiError } from "@/lib/api-client";
import {
  AuthResponse,
  VerificationResponse,
} from "./types";
import {
  LoginFormData,
  SignupFormData,
  VerifyOtpFormData,
} from "./schemas";

export async function loginApi(data: LoginFormData): Promise<AuthResponse> {
  await delay(600);

  if (data.email.toLowerCase() === "invalid@faultline.io" || data.password === "wrongpassword") {
    throw new ApiError(401, "Invalid email or password combination. Please try again.");
  }

  if (data.email.toLowerCase() === "unverified@faultline.io") {
    throw new ApiError(403, "Email verification required before login.", {
      unverified: true,
      email: data.email,
    });
  }

  return {
    token: "mock-jwt-token-faultline-sre",
    user: {
      id: "usr_7f81b2c4",
      name: "Elena Vance",
      email: data.email,
      avatarUrl: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop",
    },
    workspace: {
      id: "ws_4409ef12",
      slug: "acme-cloud",
      name: "Acme Cloud",
    },
  };
}

export async function signupApi(data: SignupFormData): Promise<VerificationResponse> {
  await delay(700);

  if (data.email.toLowerCase() === "exists@faultline.io") {
    throw new ApiError(409, "An account with this email address already exists.");
  }

  return {
    status: "pending_verification",
    email: data.email,
    expiresInSeconds: 600,
  };
}

export async function verifyOtpApi(
  email: string,
  data: VerifyOtpFormData
): Promise<AuthResponse> {
  await delay(600);

  if (data.code === "999999") {
    throw new ApiError(410, "Verification code has expired. Please request a new code.");
  }

  if (data.code === "000000") {
    throw new ApiError(400, "Invalid verification code. Please check and try again.");
  }

  return {
    token: "mock-jwt-token-verified",
    user: {
      id: "usr_8271ab99",
      name: email.split("@")[0],
      email: email,
    },
    workspace: {
      id: "ws_4409ef12",
      slug: "acme-cloud",
      name: "Acme Cloud",
    },
  };
}

export async function resendOtpApi(email: string): Promise<{ success: boolean; message: string }> {
  await delay(500);
  return {
    success: true,
    message: `A fresh 6-digit verification code has been dispatched to ${email}.`,
  };
}

