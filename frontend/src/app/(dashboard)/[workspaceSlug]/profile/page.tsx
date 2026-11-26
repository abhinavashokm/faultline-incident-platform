"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/use-toast";
import { useAuth } from "@/features/auth/auth-context";
import { useCurrentUser, useUpdateCurrentUserName } from "@/features/auth/hooks";
import type { CurrentUserResponse } from "@/features/auth/types";

function PersonalInformationForm({ user }: { user: CurrentUserResponse }) {
  const [draft, setDraft] = useState<string>();
  const name = draft ?? user.full_name;
  const savedName = name.trim();
  const update = useUpdateCurrentUserName();
  const canSave = Boolean(savedName) && savedName !== user.full_name && !update.isPending;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave) return;

    update.mutate(savedName, {
      onSuccess: () => {
        setDraft(undefined);
        toast({ title: "Personal information updated", variant: "success" });
      },
    });
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border bg-card shadow-level-1">
      <fieldset disabled={update.isPending} className="min-w-0 space-y-5 p-5 sm:p-6">
        <div className="space-y-2">
          <Label htmlFor="profile-name">Full name</Label>
          <Input
            id="profile-name"
            autoComplete="name"
            value={name}
            onChange={(event) => setDraft(event.target.value)}
            maxLength={255}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="profile-email">Email address</Label>
          <Input
            id="profile-email"
            type="email"
            value={user.email}
            readOnly
            aria-describedby="profile-email-help"
            className="bg-canvas text-text-secondary"
          />
          <p id="profile-email-help" className="text-body-sm text-text-secondary">
            Your email address is read-only.
          </p>
        </div>
        {update.isError && <p role="alert" className="text-body-sm text-error">{update.error.message}</p>}
      </fieldset>
      <footer className="flex justify-end rounded-b-lg border-t bg-canvas px-5 py-4 sm:px-6">
        <Button type="submit" className="bg-blue-700 text-white hover:bg-blue-800 active:bg-blue-800" disabled={!canSave}>
          {update.isPending ? "Saving…" : "Save changes"}
        </Button>
      </footer>
    </form>
  );
}

export default function PersonalSettingsPage() {
  const profile = useCurrentUser();
  const { isReady, isAuthenticated } = useAuth();

  return (
    <div className="mx-auto w-full max-w-2xl space-y-5">
      <header>
        <h1 className="text-headline-md">Personal information</h1>
        <p className="mt-1 text-body-sm text-text-secondary">Manage your account name and view your email address.</p>
      </header>
      {isReady && !isAuthenticated ? (
        <div className="space-y-3 rounded-lg border bg-card p-5">
          <p className="text-body-sm text-text-secondary">Sign in to view your personal information.</p>
          <Button variant="outline" size="sm" asChild><Link href="/login">Sign in</Link></Button>
        </div>
      ) : profile.data ? (
        <PersonalInformationForm key={profile.data.id} user={profile.data} />
      ) : profile.isError ? (
        <div className="space-y-3 rounded-lg border bg-card p-5">
          <p role="alert" className="text-body-sm text-error">Couldn’t load your personal information.</p>
          <Button type="button" variant="outline" size="sm" onClick={() => void profile.refetch()}>Try again</Button>
        </div>
      ) : (
        <p role="status" className="text-body-sm text-text-secondary">Loading personal information…</p>
      )}
    </div>
  );
}
