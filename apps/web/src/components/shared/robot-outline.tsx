type RobotOutlineProps = {
  className?: string;
};

export function RobotOutline({ className }: RobotOutlineProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 520 760"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
    >
      <g opacity="0.8">
        <path d="M90 720h180l-12-52H104z" />
        <path d="M120 668h120l-14-176H134z" />
        <circle cx="178" cy="470" r="78" />
        <circle cx="178" cy="470" r="42" />
        <path d="M178 392V250" />
        <path d="M140 252c0-28 18-50 38-50s38 22 38 50v132h-76z" />
        <circle cx="178" cy="228" r="52" />
        <circle cx="178" cy="228" r="24" />
        <path d="M210 196l92-66" />
        <circle cx="328" cy="150" r="56" />
        <circle cx="328" cy="150" r="28" />
        <path d="M364 186l92 112" />
        <circle cx="458" cy="304" r="42" />
        <circle cx="458" cy="304" r="18" />
        <path d="M478 334v106" />
        <path d="M448 442h60" />
        <path d="M466 440l-10 64" />
        <path d="M490 440l6 64" />
        <path d="M456 504l-10 68" />
        <path d="M496 504l10 68" />
        <path d="M140 708L8 646" />
        <path d="M210 710l126-74" />
        <path d="M34 646l148-44" />
        <path d="M332 634l-148-28" />
        <path d="M0 752l136-84" />
        <path d="M352 670l88 82" />
      </g>
      <g opacity="0.22">
        <path d="M126 668l100-176" />
        <path d="M160 394l18-164" />
        <path d="M194 394l-16-164" />
        <path d="M292 120l72 66" />
        <path d="M292 178l72-58" />
        <path d="M438 280l40 48" />
        <path d="M438 326l40-22" />
        <path d="M152 202l52 52" />
        <path d="M204 202l-52 52" />
      </g>
    </svg>
  );
}
