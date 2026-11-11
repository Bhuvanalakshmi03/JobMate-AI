import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { documentService } from "../../../services/document-service";

export function useDocumentsList(jobId?: string) {
  return useQuery({
    queryKey: ["documents", "list", jobId ?? "all"],
    queryFn: () => documentService.listDocuments(jobId),
    retry: false,
  });
}

export function useDocumentDetail(documentId: string) {
  return useQuery({
    queryKey: ["documents", "detail", documentId],
    queryFn: () => documentService.getDocument(documentId),
    enabled: Boolean(documentId),
    retry: false,
  });
}

export function useGenerateDocumentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: {
      kind: "tailored_resume" | "cover_letter" | "application_note";
      jobId: string;
      resumeId?: string | null;
      instructions?: string | null;
      tone?: "professional" | "enthusiastic" | "concise";
    }) => {
      if (params.kind === "tailored_resume") {
        return documentService.tailorResume({
          job_id: params.jobId,
          resume_id: params.resumeId || null,
          focus_instructions: params.instructions || null,
        });
      }
      if (params.kind === "cover_letter") {
        return documentService.generateCoverLetter({
          job_id: params.jobId,
          resume_id: params.resumeId || null,
          tone: params.tone ?? "professional",
          custom_notes: params.instructions || null,
        });
      }
      return documentService.generateApplicationNote({
        job_id: params.jobId,
        resume_id: params.resumeId || null,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useUpdateDocumentMutation(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      title?: string;
      content_markdown?: string;
      create_new_version?: boolean;
    }) => documentService.updateDocument(documentId, payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["documents", "detail", updated.id], updated);
      void queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
    },
  });
}
