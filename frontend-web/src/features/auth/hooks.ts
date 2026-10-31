import { useMutation } from "@tanstack/react-query";
import { loginApi, signupApi, verifyOtpApi, resendOtpApi } from "./api";
import { LoginFormData, SignupFormData, VerifyOtpFormData } from "./schemas";

export function useLogin() {
  return useMutation({
    mutationFn: (data: LoginFormData) => loginApi(data),
  });
}

export function useSignup() {
  return useMutation({
    mutationFn: (data: SignupFormData) => signupApi(data),
  });
}

export function useVerifyEmail(email: string) {
  return useMutation({
    mutationFn: (data: VerifyOtpFormData) => verifyOtpApi(email, data),
  });
}

export function useResendOtp() {
  return useMutation({
    mutationFn: (email: string) => resendOtpApi(email),
  });
}

