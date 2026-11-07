import { ApiError, apiClient, setAccessToken } from "@/lib/api-client";
import {
  AuthResponse,
  ResendVerificationResponse,
  UserResponse,
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

export async function signupApi(data: SignupFormData): Promise<UserResponse> {
  return await apiClient.post<UserResponse>("/api/v1/auth/signup", {
    full_name: data.name,
    email: data.email,
    password: data.password,
  });
}

export async function verifyOtpApi(
  email: string,
  data: VerifyOtpFormData
): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>("/api/v1/auth/verify-email", {
    email,
    code: data.code,
  });

  // Store access token in JS memory so user is authenticated
  setAccessToken(response.access_token);

  return response;
}

export async function resendOtpApi(
  email: string
): Promise<ResendVerificationResponse> {
  return await apiClient.post<ResendVerificationResponse>(
    "/api/v1/auth/resend-verification",
    { email }
  );
}

