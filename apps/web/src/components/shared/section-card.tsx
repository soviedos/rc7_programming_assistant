type SectionCardProps = {
  title: string;
  body: string;
  label?: string;
};

export function SectionCard({ title, body, label }: SectionCardProps) {
  return (
    <article className="section-card">
      {label ? <p className="section-card-label">{label}</p> : null}
      <h2>{title}</h2>
      <p>{body}</p>
    </article>
  );
}
