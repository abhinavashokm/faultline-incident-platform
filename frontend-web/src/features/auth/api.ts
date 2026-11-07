import { delay, ApiError, apiClient, setAccessToken } from "@/lib/api-client";
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
  const response = await apiClient.post<AuthResponse>("/api/v1/auth/login", {
    email: data.email,
    password: data.password,
  });

  // Store access token in JS memory
  setAccessToken(response.access_token);

  return response;
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
    access_token: "mock-jwt-token-verified",
    refresh_token: "mock-refresh-token",
    token_type: "bearer",
    expires_in: 900,
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

