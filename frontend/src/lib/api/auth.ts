import { apiClient } from "./client";
import type { User } from "@/types/api";

export async function register(data: { username: string; email: string; password: string }) {
  return apiClient<User>("/auth/register/", { method: "POST", body: data });
}

export async function login(data: { username: string; password: string }) {
  const res = await apiClient<{ access: string; refresh: string }>("/auth/login/", {
    method: "POST",
    body: data,
  });
  localStorage.setItem("access_token", res.access);
  localStorage.setItem("refresh_token", res.refresh);
  return res;
}

export async function getMe() {
  return apiClient<User>("/user/me/");
}

export async function updateMe(data: Partial<User>) {
  return apiClient<User>("/user/me/", { method: "PATCH", body: data });
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}
