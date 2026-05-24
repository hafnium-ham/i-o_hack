"use client";

export type DubLanguage = "en" | "es" | "de";

const LANGUAGES: { code: DubLanguage; flag: string }[] = [
  { code: "en", flag: "🇬🇧" },
  { code: "es", flag: "🇪🇸" },
  { code: "de", flag: "🇩🇪" },
];

type Props = {
  selected: DubLanguage;
  onChange: (lang: DubLanguage) => void;
};

export default function DubSelector({ selected, onChange }: Props) {
  return (
    <div className="flex flex-col gap-2">
      <span
        className="text-xs font-black uppercase tracking-widest"
        style={{ color: "var(--orange)" }}
      >
        Dub Language
      </span>
      <div className="flex gap-3">
        {LANGUAGES.map(({ code, flag }) => (
          <button
            key={code}
            onClick={() => onChange(code)}
            className="text-3xl transition-all"
            style={{
              transform: selected === code ? "scale(1.2)" : "scale(1)",
            }}
          >
            {flag}
          </button>
        ))}
      </div>
    </div>
  );
}
