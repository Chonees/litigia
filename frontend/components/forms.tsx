"use client";

import { Label, Input, Select, Textarea } from "@/components/ui";

export function JurisprudenciaForm() {
  return (
    <>
      <div>
        <Label>Descripción del caso</Label>
        <Textarea
          name="descripcion"
          placeholder="Ej: Mi cliente sufrió un accidente laboral en una obra en construcción. La ART le rechazó el siniestro alegando que no estaba en relación de dependencia."
          style={{ height: "8rem" }}
          required
        />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
        <div>
          <Label>Jurisdicción</Label>
          <Select name="jurisdiccion">
            <option value="">Todas</option>
            <option value="CABA">CABA</option>
            <option value="Buenos Aires">Prov. Buenos Aires</option>
            <option value="Nacional">Nacional</option>
            <option value="Federal">Federal</option>
            <option value="Mendoza">Mendoza</option>
            <option value="Cordoba">Córdoba</option>
            <option value="Santa Fe">Santa Fe</option>
          </Select>
        </div>
        <div>
          <Label>Fuero</Label>
          <Select name="fuero">
            <option value="">Todos</option>
            <option value="civil">Civil</option>
            <option value="laboral">Laboral</option>
            <option value="penal">Penal</option>
            <option value="comercial">Comercial</option>
            <option value="contencioso administrativo">Cont. Administrativo</option>
            <option value="familia">Familia</option>
          </Select>
        </div>
        <div>
          <Label>Resultados</Label>
          <Select name="top_k">
            <option value="5">5 fallos</option>
            <option value="10">10 fallos</option>
            <option value="15">15 fallos</option>
            <option value="20">20 fallos</option>
          </Select>
        </div>
      </div>
    </>
  );
}

export function EscritoForm() {
  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
        <div>
          <Label>Tipo de escrito</Label>
          <Select name="tipo" required>
            <option value="">Seleccionar...</option>
            <option value="contestacion_demanda">Contestación de demanda</option>
            <option value="demanda">Demanda</option>
            <option value="recurso_apelacion">Recurso de apelación</option>
            <option value="recurso_extraordinario">Recurso extraordinario</option>
            <option value="amparo">Amparo</option>
            <option value="medida_cautelar">Medida cautelar</option>
            <option value="alegato">Alegato</option>
            <option value="expresion_agravios">Expresión de agravios</option>
          </Select>
        </div>
        <div>
          <Label>Fuero</Label>
          <Select name="fuero" required>
            <option value="">Seleccionar...</option>
            <option value="civil">Civil</option>
            <option value="laboral">Laboral</option>
            <option value="penal">Penal</option>
            <option value="comercial">Comercial</option>
            <option value="familia">Familia</option>
          </Select>
        </div>
        <div>
          <Label>Posición procesal</Label>
          <Select name="posicion" required>
            <option value="">Seleccionar...</option>
            <option value="actor">Actor</option>
            <option value="demandado">Demandado</option>
            <option value="tercero">Tercero citado</option>
          </Select>
        </div>
        <div>
          <Label>Jurisdicción</Label>
          <Select name="jurisdiccion" required>
            <option value="">Seleccionar...</option>
            <option value="CABA">CABA</option>
            <option value="Buenos Aires">Prov. Buenos Aires</option>
            <option value="Nacional">Nacional</option>
          </Select>
        </div>
      </div>
      <div>
        <Label>Tema</Label>
        <Input
          name="tema"
          placeholder="Ej: Daños y perjuicios por accidente de tránsito"
          required
        />
      </div>
      <div>
        <Label>Datos del caso</Label>
        <Textarea
          name="datos_caso"
          placeholder="Describí los hechos, las partes, la pretensión, y cualquier dato relevante..."
          style={{ height: "9rem" }}
          required
        />
      </div>
      <div className="flex gap-3">
        <span className="inline-block px-3 py-1 text-[10px] tracking-wide uppercase font-medium border-l-2 border-l-[var(--primary)] bg-[var(--container)] text-[var(--primary)]">
          Auto-Citation Enabled
        </span>
        <span className="inline-block px-3 py-1 text-[10px] tracking-wide uppercase font-medium border-l-2 border-l-[var(--primary)] bg-[var(--container)] text-[var(--primary)]">
          Tone: Formal / Authoritative
        </span>
      </div>
    </>
  );
}

export function ResumenForm() {
  return (
    <div>
      <Label>Texto del fallo</Label>
      <Textarea
        name="texto_fallo"
        placeholder="Pegue aquí el texto completo del fallo judicial..."
        style={{ height: "14rem", fontFamily: "monospace", fontSize: "0.75rem" }}
        required
      />
    </div>
  );
}

export function OficioForm() {
  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
        <div>
          <Label>Destinatario</Label>
          <Input
            name="destinatario"
            placeholder="Ej: AFIP, Banco Nación, Registro de la Propiedad"
            required
          />
        </div>
        <div>
          <Label>Expediente</Label>
          <Input
            name="datos_expediente"
            placeholder="Ej: Expte 12345/2024, Juzgado Civil 43, Sec. 85"
            required
          />
        </div>
      </div>
      <div>
        <Label>Motivo</Label>
        <Input
          name="motivo"
          placeholder="Ej: Solicitar información fiscal del demandado"
          required
        />
      </div>
      <div>
        <Label>Datos requeridos</Label>
        <Textarea
          name="datos_requeridos"
          placeholder="Ej: Información fiscal del CUIT 20-12345678-9, últimas 5 DDJJ de ganancias y bienes personales"
          style={{ height: "6rem" }}
          required
        />
      </div>
    </>
  );
}

export function AnalisisForm() {
  return (
    <>
      <div>
        <Label>Descripción del caso</Label>
        <Textarea
          name="descripcion"
          placeholder="Ej: Despido sin causa, empleado con 8 años de antigüedad, sueldo $500k, la empresa alega abandono de trabajo..."
          style={{ height: "8rem" }}
          required
        />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
        <div>
          <Label>Fuero</Label>
          <Select name="fuero">
            <option value="">Todos</option>
            <option value="civil">Civil</option>
            <option value="laboral">Laboral</option>
            <option value="penal">Penal</option>
            <option value="comercial">Comercial</option>
          </Select>
        </div>
        <div>
          <Label>Expedientes a analizar (10-100)</Label>
          <Input
            name="top_k"
            type="number"
            min={10}
            max={100}
            defaultValue={50}
            required
          />
        </div>
        <div>
          <Label>Calidad de análisis</Label>
          <Select name="tier">
            <option value="premium">Premium — Sonnet + Opus</option>
            <option value="standard">Standard — Haiku + Opus</option>
            <option value="economy">Economy — Haiku + Sonnet</option>
          </Select>
        </div>
      </div>
      <label className="flex items-center gap-3 cursor-pointer group">
        <input type="checkbox" name="transparency" className="w-4 h-4 accent-[var(--primary)]" />
        <div>
          <span className="text-sm font-semibold text-[var(--on-surface)] group-hover:text-[var(--primary)] transition-colors">
            Transparencia — ver cómo razonó cada agente
          </span>
          <span className="block text-[10px] text-[var(--muted)]">
            Cada agente explica paso a paso cómo llegó a su conclusión. Aumenta el costo ~40%.
          </span>
        </div>
      </label>
    </>
  );
}
