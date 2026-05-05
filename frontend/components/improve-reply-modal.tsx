"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button, Textarea } from "@/components/ui";

export function ImproveReplyModal({
  conversationId,
  messageId,
  onClose,
}: {
  conversationId: string;
  messageId: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const mut = useMutation({
    mutationFn: () =>
      api(
        `/conversations/${conversationId}/messages/${messageId}/improve-reply`,
        { method: "POST", json: { correction: text } }
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conversation", conversationId] });
      onClose();
    },
  });
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg border border-border bg-bg p-4">
        <h3 className="text-sm font-semibold text-fg">Improve this reply</h3>
        <p className="mt-1 text-xs text-muted">
          What should it have said? We&apos;ll add this to your FAQs and prefer
          it next time.
        </p>
        <Textarea
          rows={4}
          className="mt-3"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="mt-3 flex items-center justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={() => mut.mutate()}
            disabled={!text.trim() || mut.isPending}
          >
            Save
          </Button>
        </div>
      </div>
    </div>
  );
}
