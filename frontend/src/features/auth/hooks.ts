import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { loginApi, signupApi, verifyOtpApi, resendOtpApi, fetchCurrentUserApi, updateCurrentUserNameApi } from "./api";
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

const currentUserQueryKey = ["auth", "me"] as const;

export function useCurrentUser() {
  const { isReady, isAuthenticated } = useAuth();

  return useQuery({
    queryKey: currentUserQueryKey,
    queryFn: fetchCurrentUserApi,
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: isReady && isAuthenticated,
  });
}

export function useUpdateCurrentUserName() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateCurrentUserNameApi,
    retry: false,
    onSuccess: async (profile) => {
      await queryClient.cancelQueries({ queryKey: currentUserQueryKey, exact: true });
      queryClient.setQueryData<Awaited<ReturnType<typeof fetchCurrentUserApi>>>(
        currentUserQueryKey,
        (current) => current?.id === profile.id ? { ...current, ...profile } : current,
      );
    },
  });
}
