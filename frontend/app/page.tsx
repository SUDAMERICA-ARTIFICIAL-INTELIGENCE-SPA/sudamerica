import { redirect } from "next/navigation";

// En el build real la raíz va al dashboard autenticado. En el export estático
// (vitrina, sin backend) va al showroom, que es toda la superficie pública.
export default function RootPage() {
  redirect(process.env.STATIC_EXPORT === "1" ? "/showroom" : "/dashboard");
}
