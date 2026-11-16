import { useMutation, useQuery } from "@tanstack/react-query";
import { loginApi, signupApi, verifyOtpApi, resendOtpApi, fetchCurrentUserApi } from "./api";
import { LoginFormData, SignupFormData, VerifyOtpFormData } from "./schemas";
import { useAuth } from "./auth-context";

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

export function useCurrentUser() {
  const { isReady, isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchCurrentUserApi,
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: isReady && isAuthenticated,
  });
}


