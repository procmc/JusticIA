import { FaChalkboardTeacher, FaBookReader } from "react-icons/fa";
import { GiLockers } from "react-icons/gi";
import { BsPersonFillExclamation, BsPersonFillGear } from "react-icons/bs";
import { BiSolidReport } from "react-icons/bi";
import { AiOutlineHome } from "react-icons/ai";
import { FaHome } from "react-icons/fa";

export const menuItems = [
  {
    id: 0,
    label: "Inicio",
    icon: FaHome,
    link: "/",
  },
  {
    id: 1,
    label: "Administración",
    icon: BsPersonFillGear,
    subItems: [
      { label: "Administradores", link: "/administrador/admin" },
      { label: "Docentes", link: "/administrador/docentes" },
      { label: "Estudiantes", link: "/administrador/estudiantes" },
      { label: "Especialidades", link: "/administrador/especialidades" },
      { label: "Tipos de sanciones", link: "/administrador/tiposSanciones" },
      { label: "Periodos de solicitud", link: "/administrador/periodoSolicitud" },
    ],
  },
  {
    id: 2,
    label: "Docente",
    icon: FaChalkboardTeacher,
    subItems: [
      {
        label: "Solicitudes de casilleros",
        subItems: [
          { label: "En espera", link: "/docente/solicitudes/1" },
          { label: "Aprobadas", link: "/docente/solicitudes/2" },
          { label: "Rechazadas", link: "/docente/solicitudes/3" },
        ],
      },
      { label: "Alertas de incidencias", link: "/docente/alertaIncidentes" },
      { label: "Crear usuarios", link: "/docente/crearUsuarios" },
    ],
  },
  {
    id: 3,
    label: "Casillero",
    icon: GiLockers,
    link: "/casillero/armario",
  },
  {
    id: 4,
    label: "Estudiante",
    icon: FaBookReader,
    subItems: [
      {label: "Estado solicitud", link: "/estudiante/estadoSolicitud",},
      { label: "Solicitud casillero", link: "/estudiante/solicitudCasillero" },
      { label: "Mi Locker", link: "/estudiante/miLoker" },
      { label: "Renuncia", link: "/estudiante/renunciarCasillero" },
    ],
  },
  {
    id: 5,
    label: "Incidente",
    icon: BsPersonFillExclamation,
    subItems: [{ label: "Lista de incidentes", link: "/incidente/listaIncidentes" }],
  },
  {
    id: 6,
    label: "Informe",
    icon: BiSolidReport,
    link: "/informe/informes",
  },
];