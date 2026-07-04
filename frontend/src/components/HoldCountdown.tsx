import { useEffect, useState } from "react";

import { isHoldExpired, secondsUntil } from "@/api/normalize";

interface HoldCountdownProps {
  expiresAt: string | null;
  onExpired?: () => void;
}

function formatTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export function HoldCountdown({ expiresAt, onExpired }: HoldCountdownProps) {
  const [remaining, setRemaining] = useState<number | null>(() => secondsUntil(expiresAt));

  useEffect(() => {
    const tick = () => {
      const next = secondsUntil(expiresAt);
      setRemaining(next);
      if (isHoldExpired(expiresAt)) {
        onExpired?.();
      }
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [expiresAt, onExpired]);

  if (!expiresAt) {
    return null;
  }

  if (remaining === null || remaining <= 0) {
    return <p className="countdown countdown--expired">Hold expired</p>;
  }

  return (
    <p className="countdown" aria-live="polite">
      Hold expires in <strong>{formatTime(remaining)}</strong>
    </p>
  );
}
