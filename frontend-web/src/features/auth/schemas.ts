import { z } from "zod";

export const loginSchema = z.object({
  email: z
    .string()
    .min(1, "Work email is required")
    .email("Please enter a valid work email address"),
  password: z
    .string()
    .min(1, "Password is required"),
  remember: z.boolean().default(false).optional(),
});

export type LoginFormData = z.infer<typeof loginSchema>;

export const signupSchema = z
  .object({
    name: z
      .string()
      .min(2, "Full name must be at least 2 characters")
      .max(64, "Name is too long"),
    email: z
      .string()
      .min(1, "Work email is required")
      .email("Please enter a valid work email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Include at least one uppercase letter")
      .regex(/[0-9]/, "Include at least one number"),
    confirmPassword: z.string().min(1, "Please confirm your password"),
    terms: z.boolean().refine((val) => val === true, {
      message: "You must agree to the Terms of Service and Privacy Policy",
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

export type SignupFormData = z.infer<typeof signupSchema>;

export const verifyOtpSchema = z.object({
  code: z
    .string()
    .length(6, "Passcode must be exactly 6 digits")
    .regex(/^\d+$/, "Passcode must contain numbers only"),
});

export type VerifyOtpFormData = z.infer<typeof verifyOtpSchema>;

