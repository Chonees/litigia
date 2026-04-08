"use client";

const inputClass =
  "w-full p-3 border border-[var(--color-border)] rounded-lg bg-white focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent focus:outline-none transition-all text-sm";

const selectClass =
  "p-3 border border-[var(--color-border)] rounded-lg bg-white focus:ring-2 focus:ring-[var(--color-primary)] focus:outline-none transition-all text-sm";

const textareaClass = `${inputClass} resize-none font-serif`;

export function JurisprudenciaForm() {
  return (
    <>
      <div>
        <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
          Descripcion del caso
        </label>
        <textarea
          name="descripcion"
          placeholder="Ej: Mi cliente sufrio un accidente laboral en una obra en construccion. La ART le rechazo el siniestro alegando que no estaba en relacion de dependencia."
          className={`${textareaClass} h-32`}
          required
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
            Jurisdiccion
          </label>
          <select name="jurisdiccion" className={selectClass}>
            <option value="">Todas</option>
            <option value="CABA">CABA</option>
            <option value="Buenos Aires">Prov. Buenos Aires</option>
            <option value="Nacional">Nacional</option>
            <option value="Federal">Federal</option>
            <option value="Mendoza">Mendoza</option>
            <option value="Cordoba">Cordoba</option>
            <option value="Santa Fe">Santa Fe</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
            Fuero
          </label>
          <select name="fuero" className={selectClass}>
            <option value="">Todos</option>
            <option value="civil">Civil</option>
            <option value="laboral">Laboral</option>
            <option value="penal">Penal</option>
            <option value="comercial">Comercial</option>
            <option value="contencioso administrativo">Cont. Administrativo</option>
            <option value="familia">Familia</option>
          </select>
        </div>
      </div>
    </>
  );
}

export function EscritoForm() {
  return (
    <>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
            Tipo de escrito
          </label>
          <select name="tipo" className={selectClass} required>
            <option value="">Seleccionar...</option>
            <option value="contestacion_demanda">Contestacion de demanda</option>
            <option value="demanda">Demanda</option>
            <option value="recurso_apelacion">Recurso de apelacion</option>
            <option value="recurso_extraordinario">Recurso extraordinario</option>
            <option value="amparo">Amparo</option>
            <option value="medida_cautelar">Medida cautelar</option>
            <option value="alegato">Alegato</option>
            <option value="expresion_agravios">Expresion de agravios</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
            Fuero
          </label>
          <select name="fuero" className={selectClass} required>
            <option value="">Seleccionar...</option>
            <option value="civil">Civil</option>
            <option value="laboral">Laboral</option>
            <option value="penal">Penal</option>
            <option value="comercial">Comercial</option>
            <option value="familia">Familia</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
            Posicion procesal
          </label>
          <select name="posicion" className={selectClass} required>
            <option value="">Seleccionar...</option>
            <option value="actor">Actor</option>
            <option value="demandado">Demandado</option>
            <option value="tercero">Tercero citado</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
            Jurisdiccion
          </label>
          <select name="jurisdiccion" className={selectClass} required>
            <option value="">Seleccionar...</option>
            <option value="CABA">CABA</option>
            <option value="Buenos Aires">Prov. Buenos Aires</option>
            <option value="Nacional">Nacional</option>
          </select>
        </div>
      </div>
      <div>
        <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
          Tema
        </label>
        <input
          name="tema"
          placeholder="Ej: Danos y perjuicios por accidente de transito"
          className={inputClass}
          required
        />
      </div>
      <div>
        <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
          Datos del caso
        </label>
        <textarea
          name="datos_caso"
          placeholder="Describi los hechos, las partes, la pretension, y cualquier dato relevante..."
          className={`${textareaClass} h-36`}
          required
        />
      </div>
    </>
  );
}

export function ResumenForm() {
  return (
    <div>
      <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
        Texto del fallo
      </label>
      <textarea
        name="texto_fallo"
        placeholder="Pega el texto completo del fallo aca..."
        className={`${textareaClass} h-56 font-mono text-xs`}
        required
      />
    </div>
  );
}

export function OficioForm() {
  return (
    <>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
            Destinatario
          </label>
          <input
            name="destinatario"
            placeholder="Ej: AFIP, Banco Nacion, Registro de la Propiedad"
            className={inputClass}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
            Expediente
          </label>
          <input
            name="datos_expediente"
            placeholder="Ej: Expte 12345/2024, Juzgado Civil 43, Sec. 85"
            className={inputClass}
            required
          />
        </div>
      </div>
      <div>
        <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
          Motivo
        </label>
        <input
          name="motivo"
          placeholder="Ej: Solicitar informacion fiscal del demandado"
          className={inputClass}
          required
        />
      </div>
      <div>
        <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
          Datos requeridos
        </label>
        <textarea
          name="datos_requeridos"
          placeholder="Ej: Informacion fiscal del CUIT 20-12345678-9, ultimas 5 DDJJ de ganancias y bienes personales"
          className={`${textareaClass} h-24`}
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
        <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
          Descripcion del caso
        </label>
        <textarea
          name="descripcion"
          placeholder="Ej: Despido sin causa, empleado con 8 anos de antiguedad, sueldo $500k, la empresa alega abandono de trabajo..."
          className={`${textareaClass} h-32`}
          required
        />
      </div>
      <div>
        <label className="block text-sm font-semibold text-[var(--color-primary)] mb-1.5">
          Fuero
        </label>
        <select name="fuero" className={selectClass}>
          <option value="">Todos</option>
          <option value="civil">Civil</option>
          <option value="laboral">Laboral</option>
          <option value="penal">Penal</option>
          <option value="comercial">Comercial</option>
        </select>
      </div>
    </>
  );
}
