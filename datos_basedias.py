# -*- coding: utf-8 -*-
"""
BASE DÍAS — Servidores y queries (NV Vale Amigo / NV Viva Vale / RP Vale).
Los queries están pegados TAL CUAL de los archivos del usuario; lo ÚNICO que se
cambió es la fecha de corte para poder elegir el día (igual que en cobranza):
  - Queries NV (MySQL):  `cc_closure.date = CURDATE()`  ->  `cc_closure.date = @FechaCorte`
    (antes de ejecutar el query se corre `SET @FechaCorte = 'AAAA-MM-DD'`).
  - Query RP (SQL Server): `DECLARE @currentDate DATETIME = GETDATE();`
    -> `DECLARE @currentDate DATETIME = '__FECHA__';` (se sustituye la fecha elegida).
"""

# ------------------------------------------------------------------
# SERVIDORES POR MARCA
#   - Cada marca usa su query: VALE AMIGO -> NV_VALE, VALE AMIGO PERU ->
#     NV_VALE_PERU (su esquema es distinto: ubigeo_code, joins propios),
#     VIVA VALE -> NV_VIVA_VALE y RP VALE -> RP_VALE (SQL Server).
# ------------------------------------------------------------------
# Cada marca tiene sus PROPIAS credenciales (mandan sobre las del proyecto).
SERVIDORES_BASE_DIAS = [
    {'nombre': 'VALE AMIGO',
     'motor': 'mysql',
     'host': 'valeamigo.cfogdzqqzoae.us-east-1.rds.amazonaws.com',
     'db': 'valeAmigo',
     'usuario': 'ivantrejo',
     'contrasena': 'xY5mvS0TSIP2/C7ML6iv8g==',
     'query': 'NV_VALE',
     'archivo': 'Cartera_Base_Dias_ValeAmigo_{fecha}'},

    {'nombre': 'VALE AMIGO PERU',
     'motor': 'mysql',
     'host': 'valeamigo-peru.cfogdzqqzoae.us-east-1.rds.amazonaws.com',
     'db': 'valeAmigo',
     'usuario': 'joseavm',
     'contrasena': 'DkzBHqp85OzHO5SLqUWFeQ==',
     'query': 'NV_VALE_PERU',   # query propio: el esquema de Peru es distinto (ubigeo_code, etc.)
     'archivo': 'Cartera_Base_Dias_ValeAmigoPeru_{fecha}'},

    {'nombre': 'VIVA VALE',
     'motor': 'mysql',
     'host': 'vivavale.cfogdzqqzoae.us-east-1.rds.amazonaws.com',
     'db': 'vivavale',
     'usuario': 'Ivantrejo',
     'contrasena': '6oRxvZx59EvEwrqDwP1gcQ==',
     'query': 'NV_VIVA_VALE',
     'archivo': 'CarteraBaseDias_VivaVale_{fecha}'},

    {'nombre': 'RP VALE',
     'motor': 'sqlserver',
     'host': 'rapivale.ceh2z2qop3sh.us-east-2.rds.amazonaws.com',
     'db': 'rapivale',
     'usuario': 'jtrejol',
     'contrasena': 'Oe#sjir12',
     'query': 'RP_VALE',
     'archivo': 'base_dias_{fecha}'},
]

QUERY_NV_VALE = r"""
SELECT 
    IFNULL(cdir.name, 'SIN DIRECCION') AS 'Sub Direccion',
    cdiv.name AS 'Division',
    cr.name AS 'Region',
    cb.name AS 'Sucursal',
    
    DATE_FORMAT(cc_closure.date, '%d/%m/%Y') AS 'Fecha de Corte',
    
    CAST(cd.number AS SIGNED) AS 'Numero',
    CONCAT_WS(' ', cpn.name, cpn.middle_name, cpn.last_name, cpn.second_last_name) AS 'Nombre',
    CASE 
        WHEN cd.id_category = 1 THEN 'Bronce'
        WHEN cd.id_category = 2 THEN 'Plata'
        WHEN cd.id_category = 3 THEN 'Oro'
        WHEN cd.id_category = 4 THEN 'Diamante'
        WHEN cd.id_category = 5 THEN 'Platino'
        ELSE 'Sin Categoria'
    END AS 'Categoria',
    IFNULL(coord.name, '') AS 'Coordinacion',
    
    IFNULL(cce.customers_with_pending_purchases, 0) AS 'Clientes con Compras Pendientes',
    IFNULL(cce.total_pending_purchases, 0) AS 'Total de Compras Pendientes',
    
    IFNULL(cce.due_balance, 0.00) AS 'Vencido',
    IFNULL(cce.payable_balance, 0.00) AS 'Exigible',
    IFNULL(cce.current_balance, 0.00) AS 'Vigente',
    IFNULL(cce.total_balance, 0.00) AS 'Total',
    
    IFNULL(cce.placed, 0.00) AS 'Colocado',
    IFNULL(cce.placed_personal_loan, 0.00) AS 'Colocado PP',
    IFNULL(cce.placed_personal_loan_special, 0.00) AS 'Colocado PP Especial',
    
    IFNULL(cce.`available`, 0.00) AS 'Disponible',
    IFNULL(cce.`limit`, 0.00) AS 'Limite de Credito',
    
    cce.due_days AS 'Mora Actual',
    IFNULL(cce.max_due_days, 0) AS 'Mora Maxima',
    IFNULL(cce.total_balance_without_discount, 0.00) AS 'Saldo Sin Descuento',
    
    CASE 
        WHEN IFNULL(cce.total_thrift_amount, 0) > 0 OR cce.thrift_activation_date IS NOT NULL THEN 'SI' 
        ELSE 'NO' 
    END AS 'Ahorro Amigo',
    IFNULL(DATE_FORMAT(cce.thrift_activation_date, '%d/%m/%Y'), '') AS 'Fecha Activacion Ahorro Amigo',
    IFNULL(cce.total_thrift_amount, 0.00) AS 'Total Ahorro Amigo',
    
    IFNULL(DATE_FORMAT(cce.activation_date, '%d/%m/%Y'), '') AS 'Fecha Activacion',
    IFNULL(DATE_FORMAT((
        SELECT MAX(cp.date) 
        FROM credit_puchases cp 
        WHERE cp.id_distributor = cd.id_distributor AND cp.status = 1
    ), '%d/%m/%Y'), '') AS 'Fecha Ultimo Canje',
    IFNULL(DATE_FORMAT(cce.last_payment_date, '%d/%m/%Y'), '') AS 'Fecha Ultimo Pago',
    
    -- Diccionario de Estatus Completo (Aquí ya puedes ponerle los nombres reales a los "Misterios")
    CASE
                WHEN cce.status = 1 THEN 'Pendiente'
                WHEN cce.status = 2 THEN 'Autorizado'
                WHEN cce.status = 3 THEN 'Bloqueado'
                WHEN cce.status = 4 THEN 'Cancelado'
                WHEN cce.status = 5 THEN 'Dictaminado'
                WHEN cce.status = 6 THEN 'Liquidado'
                WHEN cce.status = 7 THEN 'Bloqueado (Automatico)'
                WHEN cce.status = 8 THEN 'Dictaminado'
                WHEN cce.status = 9 THEN 'Pendiente Primer Libro de vales'
                WHEN cce.status = 10 THEN 'Convenio de Salida'
                WHEN cce.status = 17 THEN 'RECUPERACION DE CREDITO' 
                WHEN cce.status = 18 THEN 'DICTAMINADO VENTA CARTERA'
                WHEN cce.status = 19 THEN 'Finada'
                WHEN cce.status = 20 THEN 'Quebranto'
                WHEN cce.status = 21 THEN 'Consideración'
                WHEN cce.status = 22 THEN 'Liquidación Anticipada'
                WHEN cce.status = 23 THEN 'Robo'
                WHEN cce.status = 24 THEN 'Restructura'
                WHEN cce.status = 25 THEN 'CONVENIO DE PAGO'
                WHEN cce.status = 26 THEN 'Demandado'
                WHEN cce.status = 27 THEN 'Fraudes y Quebrantos'
                WHEN cce.status = 28 THEN 'GescoD'
                WHEN cce.status = 29 THEN 'GescoD Reestructura'
                WHEN cce.status = 30 THEN 'GescoD Quebranto'
                WHEN cce.status = 31 THEN 'GescoD Liquidado'
                WHEN cce.status = 33 THEN 'UNOM'
                WHEN cce.status = 34 THEN 'UNOM Reestructura'
                WHEN cce.status = 35 THEN 'UNOM Quebranto'
                WHEN cce.status = 36 THEN 'UNOM Liquidado'
                WHEN cce.status = 38 THEN 'Quebranto liquidado'
                WHEN cce.status = 39 THEN 'Restructura liquidada'
                WHEN cce.status = 99 THEN 'Eliminado'
                ELSE 'STATUS NO DEFINIDO'
    END AS 'Status',
    
    IFNULL(TIMESTAMPDIFF(MONTH, cce.activation_date, cc_closure.date), 0) AS 'Antiguedad',
    
    IFNULL(ca.street, '') AS 'Calle y #',
    '' AS 'Capital', 
    IFNULL(ca.zipcode, '') AS 'Ubigeo',
    IFNULL(ca.city, '') AS 'Provincia',
    IFNULL(ca.state, '') AS 'Departamento',
    
    IFNULL((
        SELECT MAX(cp_phone.number) 
        FROM credit_phones cp_phone 
        WHERE cp_phone.id_person = cpn.id_person AND cp_phone.status = 1
    ), '') AS 'Telefono',
    
    IFNULL(cce.distributor_insurances_balance, 0.00) AS 'Protecciones',
    IFNULL(cce.unom, '') AS 'UNOM'

FROM credit_distributors cd
INNER JOIN closure_closures_entries cce ON cd.id_distributor = cce.id_distributor
-- Aquí cambias la fecha cuando quieras el corte de otro día
INNER JOIN closure_closures cc_closure ON cc_closure.id_closure = cce.id_closure AND cc_closure.date = @FechaCorte

INNER JOIN core_branches cb ON cb.id_branch = cd.id_branch
INNER JOIN credit_persons cpn ON cpn.id_person = cd.id_person

LEFT JOIN core_regions cr ON cr.id_region = cb.id_region
LEFT JOIN core_divisions cdiv ON cdiv.id_division = cr.id_division
LEFT JOIN core_directions cdir ON cdir.id_direction = cdiv.id_direction
LEFT JOIN credit_addresses ca ON ca.id_address = cpn.id_address
LEFT JOIN collection_coordinations coord ON coord.id_coordination = cce.id_coordination

-- FILTRO MAESTRO: Traer TODO, EXCEPTO el 5 (Dictaminado) y el 99 (Eliminado)
WHERE cce.status NOT IN (5, 99)

ORDER BY cb.name, cd.number;
"""

QUERY_NV_VIVA_VALE = r"""
SELECT 
    IFNULL(cdir.name, 'SIN DIRECCION') AS 'Sub Direccion',
    cdiv.name AS 'Division',
    cr.name AS 'Region',
    cb.name AS 'Sucursal',
    
    DATE_FORMAT(cc_closure.date, '%d/%m/%Y') AS 'Fecha de Corte',
    
    CAST(cd.number AS SIGNED) AS 'Numero',
    CONCAT_WS(' ', cpn.name, cpn.middle_name, cpn.last_name, cpn.second_last_name) AS 'Nombre',
    CASE 
        WHEN cd.id_category = 1 THEN 'Junior'
        WHEN cd.id_category = 2 THEN 'Master'
        WHEN cd.id_category = 3 THEN 'Super'
        ELSE 'Sin Categoria'
    END AS 'Categoria',
    IFNULL(coord.name, '') AS 'Coordinacion',
    
    -- 1. Columna original para el conteo de personas (Viva Vale)
    IFNULL(cce.customers_with_pending_purchases, 0) AS 'Clientes con Compras Pendientes',
    
    -- 2. PARCHE MATEMÁTICO: Sumamos el dinero ('amount') directo desde la tabla de compras
    IFNULL((
        SELECT SUM(cp.amount) 
        FROM credit_puchases cp 
        WHERE cp.id_distributor = cd.id_distributor AND cp.status = 1
    ), 0.00) AS 'Total de Compras Pendientes',
    
    IFNULL(cce.due_balance, 0.00) AS 'Vencido',
    IFNULL(cce.payable_balance, 0.00) AS 'Exigible',
    IFNULL(cce.current_balance, 0.00) AS 'Vigente',
    IFNULL(cce.total_balance, 0.00) AS 'Total',
    
    IFNULL(cce.placed, 0.00) AS 'Colocado',
    IFNULL(cce.placed_personal_loan, 0.00) AS 'Colocado PP',
    IFNULL(cce.placed_personal_loan_special, 0.00) AS 'Colocado PP Especial',
    
    IFNULL(cce.`available`, 0.00) AS 'Disponible',
    IFNULL(cce.`limit`, 0.00) AS 'Limite de Credito',
    
    cce.due_days AS 'Mora Actual',
    IFNULL(cce.max_due_days, 0) AS 'Mora Maxima',
    IFNULL(cce.total_balance_without_discount, 0.00) AS 'Saldo Sin Descuento',
    
    CASE 
        WHEN IFNULL(cce.total_thrift_amount, 0) > 0 OR cce.thrift_activation_date IS NOT NULL THEN 'SI' 
        ELSE 'NO' 
    END AS 'Ahorro Amigo',
    IFNULL(DATE_FORMAT(cce.thrift_activation_date, '%d/%m/%Y'), '') AS 'Fecha Activacion Ahorro Amigo',
    IFNULL(cce.total_thrift_amount, 0.00) AS 'Total Ahorro Amigo',
    
    IFNULL(DATE_FORMAT(cce.activation_date, '%d/%m/%Y'), '') AS 'Fecha Activacion',
    IFNULL(DATE_FORMAT((
        SELECT MAX(cp.date) 
        FROM credit_puchases cp 
        WHERE cp.id_distributor = cd.id_distributor AND cp.status = 1
    ), '%d/%m/%Y'), '') AS 'Fecha Ultimo Canje',
    IFNULL(DATE_FORMAT(cce.last_payment_date, '%d/%m/%Y'), '') AS 'Fecha Ultimo Pago',
    
    CASE
        WHEN cce.status = 1 THEN 'Pendiente'
        WHEN cce.status = 2 THEN 'Autorizado'
        WHEN cce.status = 3 THEN 'Bloqueado'
        WHEN cce.status = 4 THEN 'Cancelado'
        WHEN cce.status = 5 THEN 'Dictaminado'
        WHEN cce.status = 6 THEN 'Liquidado'
        WHEN cce.status = 7 THEN 'Bloqueado (Automatico)'
        WHEN cce.status = 8 THEN 'Dictaminado'
        WHEN cce.status = 9 THEN 'Pendiente Primer Libro de vales'
        WHEN cce.status = 10 THEN 'Convenio de Salida'
        WHEN cce.status = 17 THEN 'RECUPERACION DE CREDITO' 
        WHEN cce.status = 18 THEN 'DICTAMINADO VENTA CARTERA'
        WHEN cce.status = 19 THEN 'Finada'
        WHEN cce.status = 20 THEN 'Quebranto'
        WHEN cce.status = 21 THEN 'Consideración'
        WHEN cce.status = 22 THEN 'Liquidación Anticipada'
        WHEN cce.status = 23 THEN 'Robo'
        WHEN cce.status = 24 THEN 'Reestructura'
        WHEN cce.status = 25 THEN 'CONVENIO DE PAGO'
        WHEN cce.status = 26 THEN 'Demandado'
        WHEN cce.status = 27 THEN 'Fraude/Quebranto/Restructura (27)'
        WHEN cce.status = 28 THEN 'Quebranto Liquidado'
        WHEN cce.status = 29 THEN 'Restructura liquidada'
        WHEN cce.status = 30 THEN 'Convenio de pago liquidado'
        WHEN cce.status = 31 THEN 'GescoD Liquidado'
        WHEN cce.status = 32 THEN 'GescoD'
        WHEN cce.status = 33 THEN 'UNOM'
        WHEN cce.status = 34 THEN 'UNOM Reestructura'
        WHEN cce.status = 35 THEN 'GescoD Liquidado'
        WHEN cce.status = 36 THEN 'UNOM Liquidado'
        WHEN cce.status = 38 THEN 'Fraude/Quebranto/Restructura (38)'
        WHEN cce.status = 39 THEN 'UNOM Liquidado'
        WHEN cce.status = 99 THEN 'Eliminado'
        ELSE 'Migrado'
    END AS 'Status',
    
    IFNULL(TIMESTAMPDIFF(MONTH, cce.activation_date, cc_closure.date), 0) AS 'Antiguedad',
    
    IFNULL(ca.street, '') AS 'Calle y #',
    '' AS 'Capital', 
    IFNULL(ca.zipcode, '') AS 'Ubigeo',
    IFNULL(ca.city, '') AS 'Provincia',
    IFNULL(ca.state, '') AS 'Departamento',
    
    IFNULL((
        SELECT MAX(cp_phone.number) 
        FROM credit_phones cp_phone 
        WHERE cp_phone.id_person = cpn.id_person AND cp_phone.status = 1
    ), '') AS 'Telefono',
    
    IFNULL(cce.distributor_insurances_balance, 0.00) AS 'Protecciones',
    IFNULL(cce.unom, '') AS 'UNOM'

FROM credit_distributors cd
INNER JOIN closure_closures_entries cce ON cd.id_distributor = cce.id_distributor
-- Recuerda ajustar la fecha de tu corte según necesites
INNER JOIN closure_closures cc_closure ON cc_closure.id_closure = cce.id_closure AND cc_closure.date = @FechaCorte

INNER JOIN core_branches cb ON cb.id_branch = cd.id_branch
INNER JOIN credit_persons cpn ON cpn.id_person = cd.id_person

LEFT JOIN core_regions cr ON cr.id_region = cb.id_region
LEFT JOIN core_divisions cdiv ON cdiv.id_division = cr.id_division
LEFT JOIN core_directions cdir ON cdir.id_direction = cdiv.id_direction
LEFT JOIN credit_addresses ca ON ca.id_address = cpn.id_address
LEFT JOIN collection_coordinations coord ON coord.id_coordination = cce.id_coordination

-- FILTRO MAESTRO: Traer TODO, EXCEPTO los IDs indicados (Dictaminados, Venta Cartera y Demandados)
WHERE cce.status NOT IN (5, 8, 18, 26)

ORDER BY cb.name, cd.number;
"""

QUERY_RP_VALE = r"""
DECLARE @currentDate DATETIME = '__FECHA__'; 

SELECT 
    cb.name AS 'Sucursal',
    cd.id_distributor AS 'ID Socio',
    CONCAT_WS(' ', cpn.first_name, cpn.middle_name, cpn.last_name, cpn.second_last_name) AS 'Nombre',
    
    CASE 
        WHEN cce.periodicity = 2 THEN 'Semanal'
        WHEN cce.periodicity = 3 THEN 'Quincenal'
        ELSE ISNULL(CONVERT(VARCHAR(50), cce.periodicity), '')
    END AS 'Periodicidad del Crédito', 
    
    CASE 
        WHEN cd.id_category = 1 THEN 'Principiante'
        WHEN cd.id_category = 2 THEN 'Bronce'
        WHEN cd.id_category = 3 THEN 'Plata'
        WHEN cd.id_category = 4 THEN 'Oro'
        WHEN cd.id_category = 5 THEN 'Diamante'
        WHEN cd.id_category = 6 THEN 'Bronce'
        WHEN cd.id_category = 7 THEN 'Plata'
        WHEN cd.id_category = 8 THEN 'Oro'
        WHEN cd.id_category = 9 THEN 'Platino'
        WHEN cd.id_category = 10 THEN 'Diamante'
        ELSE 'Desconocida'
    END AS 'Categoría',
    
    ISNULL(coord.name, '') AS 'Coordinación',
    ISNULL(cce.total_customers, 0) AS 'Total Clientes', 
    ISNULL(cce.due_balance, 0.00) AS 'Vencido',
    ISNULL(cce.payable_balance, 0.00) AS 'Exigible',
    ISNULL(cce.current_balance, 0.00) AS 'Vigente',
    ISNULL(cce.total_balance, 0.00) AS 'Total',
    ISNULL(cce.placed, 0.00) AS 'Colocado',
    ISNULL(cce.placed_personal_loan, 0.00) AS 'Colocado PP',
    ISNULL(cce.placed_interest_personal_loan, 0.00) AS 'Colocado Interes PP',            
    ISNULL(cce.placed_special_loan, 0.00) AS 'Colocado Préstamo Especial',
    ISNULL(cce.placed_rapishop, 0.00) AS 'Colocado Rapishop',              
    ISNULL(cce.placed_rapishop_distributor, 0.00) AS 'Colocado Rapishop Socio',        
    ISNULL(cce.placed_reactivate_loan, 0.00) AS 'Colocado Préstamo Reactivate',   
    ISNULL(cce.available, 0.00) AS 'Disponible',
    ISNULL(cce.limit, 0.00) AS 'Límite de Crédito',
    ISNULL(cce.due_days, 0) AS 'Mora Actual',
    ISNULL(cce.max_due_days, 0) AS 'Mora Máxima',
    ISNULL(cce.balance_without_discount, 0.00) AS 'Saldo sin descuento',
    
    ISNULL(CONVERT(VARCHAR(10), cce.activation_date, 103), '') AS 'Fecha Activación',
    ISNULL(CONVERT(VARCHAR(10), cce.last_swapped_date, 103), '') AS 'Fecha Ultimo Canje',
    ISNULL(CONVERT(VARCHAR(10), cce.last_payment_date, 103), '') AS 'Fecha Ultimo Pago',
    
    CASE
        WHEN cce.status = 1 THEN 'Pendiente'
        WHEN cce.status = 2 THEN 'Autorizado'
        WHEN cce.status = 3 THEN 'Bloqueado'
        WHEN cce.status = 4 THEN 'Cancelado'
        WHEN cce.status = 5 THEN 'Dictaminado'
        WHEN cce.status = 6 THEN 'Liquidado'
        WHEN cce.status = 7 THEN 'Bloqueado (Automatico)'
        WHEN cce.status = 8 THEN 'Dictaminado'
        WHEN cce.status = 9 THEN 'Pendiente Primer Libro de vales'
        WHEN cce.status = 10 THEN 'Convenio de Salida'
        WHEN cce.status = 17 THEN 'RECUPERACION DE CREDITO' 
        WHEN cce.status = 18 THEN 'DICTAMINADO VENTA CARTERA'
        WHEN cce.status = 19 THEN 'Finada'
        WHEN cce.status = 20 THEN 'Quebranto'
        WHEN cce.status = 21 THEN 'Consideración'
        WHEN cce.status = 22 THEN 'Liquidación Anticipada'
        WHEN cce.status = 23 THEN 'Robo'
        WHEN cce.status = 24 THEN 'Reestructura'
        WHEN cce.status = 25 THEN 'CONVENIO DE PAGO'
        WHEN cce.status = 26 THEN 'Demandado'
        WHEN cce.status = 27 THEN 'Fraude/Quebranto/Restructura (27)'
        WHEN cce.status = 28 THEN 'Quebranto Liquidado'
        WHEN cce.status = 29 THEN 'Restructura liquidada'
        WHEN cce.status = 30 THEN 'Convenio de pago liquidado'
        WHEN cce.status = 31 THEN 'GescoD Liquidado'
        WHEN cce.status = 32 THEN 'GescoD'
        WHEN cce.status = 33 THEN 'UNOM'
        WHEN cce.status = 34 THEN 'UNOM Reestructura'
        WHEN cce.status = 35 THEN 'GescoD Liquidado'
        WHEN cce.status = 36 THEN 'UNOM Liquidado'
        WHEN cce.status = 38 THEN 'Fraude/Quebranto/Restructura (38)'
        WHEN cce.status = 39 THEN 'UNOM Liquidado'
        WHEN cce.status = 99 THEN 'Eliminado'
        ELSE 'Migrado'
    END AS 'Status'

FROM [dbo].[credit_distributors] cd
INNER JOIN [dbo].[closure_closures_entries] cce ON cd.id_distributor = cce.id_distributor
INNER JOIN [dbo].[closure_closures] cc_closure ON cc_closure.id_closure = cce.id_closure 
    AND CONVERT(DATE, cc_closure.date) = CONVERT(DATE, @currentDate)
INNER JOIN [dbo].[core_branches] cb ON cb.id_branch = cd.id_branch
INNER JOIN [dbo].[credit_persons] cpn ON cpn.id_person = cd.id_person
LEFT JOIN [dbo].[collection_coordinations] coord ON coord.id_coordination = cce.id_coordination

WHERE cce.status NOT IN (18, 26)

ORDER BY cb.name, cd.id_distributor;
"""

QUERY_NV_VALE_PERU = r"""
SELECT 
    'DIRECCION GENERAL' AS 'Sub Dirección',
    cdiv.name AS 'División',
    cr.name AS 'Región',
    cb.name AS 'Sucursal',
    CAST(cd.number AS SIGNED) AS 'Número',
    CONCAT_WS(' ', cpn.name, cpn.middle_name, cpn.last_name, cpn.second_last_name) AS 'Nombre',
    CASE 
        WHEN cd.id_category = 1 THEN 'Bronce'
        WHEN cd.id_category = 2 THEN 'Plata'
        WHEN cd.id_category = 3 THEN 'Oro'
        WHEN cd.id_category = 4 THEN 'Diamante'
        WHEN cd.id_category = 5 THEN 'Platino'
        ELSE 'Sin Categoria'
    END AS 'Categoría',
    IFNULL(coord.name, '') AS 'Coordinacion',
    
    IFNULL(cce.customers_with_pending_purchases, 0) AS 'Clientes con Compras Pendientes',
    IFNULL(cce.total_pending_purchases, 0) AS 'Total de Compras Pendientes',
    
    IFNULL(cce.due_balance, 0.00) AS 'Vencido',
    IFNULL(cce.payable_balance, 0.00) AS 'Exigible',
    IFNULL(cce.current_balance, 0.00) AS 'Vigente',
    IFNULL(cce.total_balance, 0.00) AS 'Total',
    
    IFNULL(cce.placed, 0.00) AS 'Colocado',
    IFNULL(cce.placed_personal_loan, 0.00) AS 'Colocado PP',
    IFNULL(cce.placed_personal_loan_special, 0.00) AS 'Colocado PP Especial',
    
    IFNULL(cce.`available`, 0.00) AS 'Disponible',
    IFNULL(cce.`limit`, 0.00) AS 'Límite de Crédito',
    
    cce.due_days AS 'Mora Actual',
    IFNULL(cce.max_due_days, 0) AS 'Mora Máxima',
    IFNULL(cce.total_balance_without_discount, 0.00) AS 'Saldo Sin Descuento',
    
    CASE 
        WHEN IFNULL(cce.total_thrift_amount, 0) > 0 OR cce.thrift_activation_date IS NOT NULL THEN 'SI' 
        ELSE 'NO' 
    END AS 'Ahorro Amigo',
    IFNULL(DATE_FORMAT(cce.thrift_activation_date, '%d/%m/%Y'), '') AS 'Fecha Activación Ahorro Amigo',
    IFNULL(cce.total_thrift_amount, 0.00) AS 'Total Ahorro Amigo',
    
    IFNULL(DATE_FORMAT(cce.activation_date, '%d/%m/%Y'), '') AS 'Fecha Activación',
    IFNULL(DATE_FORMAT((
        SELECT MAX(cp.date) 
        FROM credit_puchases cp 
        WHERE cp.id_distributor = cd.id_distributor AND cp.status = 1
    ), '%d/%m/%Y'), '') AS 'Fecha Ultimo Canje',
    IFNULL(DATE_FORMAT(cce.last_payment_date, '%d/%m/%Y'), '') AS 'Fecha Ultimo Pago',
    
    CASE
        WHEN cce.status = 1 THEN 'Pendiente'
        WHEN cce.status = 2 THEN 'Autorizado'
        WHEN cce.status = 3 THEN 'Bloqueado'
        WHEN cce.status = 4 THEN 'Cancelado'
        WHEN cce.status = 5 THEN 'Dictaminado'
        WHEN cce.status = 6 THEN 'Liquidado'
        ELSE 'STATUS NO DEFINIDO'
    END AS 'Status',
    
    IFNULL(TIMESTAMPDIFF(MONTH, cce.activation_date, cc_closure.date), 0) AS 'Antigüedad',
    
    IFNULL(ca.street, '') AS 'Calle y #',
    '' AS 'Capital', 
    IFNULL(ca.ubigeo_code, '') AS 'Ubigeo',
    IFNULL(ca.city, '') AS 'Provincia',
    IFNULL(ca.state, '') AS 'Departamento',
    
    IFNULL((
        SELECT MAX(cp_phone.number) 
        FROM credit_phones cp_phone 
        WHERE cp_phone.id_person = cpn.id_person AND cp_phone.status = 1
    ), '') AS 'Teléfono',
    
    -- ¡Conexión exitosa del seguro!
    IFNULL(cce.distributor_insurances_balance, 0.00) AS 'Protecciones',
    IFNULL(cce.unom, '') AS 'UNOM'

FROM credit_distributors cd
INNER JOIN closure_closures_entries cce ON cd.id_distributor = cce.id_distributor
-- Aquí puedes cambiar la fecha cuando necesites el corte de otro día
INNER JOIN closure_closures cc_closure ON cc_closure.id_closure = cce.id_closure AND cc_closure.date = @FechaCorte
INNER JOIN core_branches cb ON cb.id_branch = cd.id_branch
INNER JOIN credit_persons cpn ON cpn.id_person = cd.id_person
INNER JOIN credit_credits cc2 ON cc2.id_distributor = cd.id_distributor

LEFT JOIN core_regions cr ON cr.id_region = cb.id_region
LEFT JOIN core_divisions cdiv ON cdiv.id_division = cr.id_division
LEFT JOIN credit_addresses ca ON ca.id_address = cpn.id_address
LEFT JOIN collection_coordinations coord ON coord.id_coordination = cce.id_coordination

ORDER BY cb.name, cd.number;
"""

QUERIES_BASE_DIAS = {
    'NV_VALE': QUERY_NV_VALE,
    'NV_VALE_PERU': QUERY_NV_VALE_PERU,
    'NV_VIVA_VALE': QUERY_NV_VIVA_VALE,
    'RP_VALE': QUERY_RP_VALE,
}
