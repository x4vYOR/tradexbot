class Trade:
    precio_entrada = 0
    precio_venta = 0
    precio_stop = 0
    cantidad = 0
    monto_compra = 0
    monto_venta = 0
    duracion = 0  # cuantas velas demoró en cerrarse
    estado = "Abierto"  # Abierto, Cerrado, Stop
    profit = 0  # Beneficio en dolares
    stop = 0  # Beneficio en dolares
    precio_minimo_anterior = 0  # Beneficio en dolares

    def __init__(self, precio, monto_compra, profit, stop, precio_minimo_anterior=0):
        self.precio_entrada = precio
        self.monto_compra = monto_compra
        self.cantidad = monto_compra / precio
        self.precio_venta = precio * profit
        self.precio_stop = precio_minimo_anterior * stop
        self.duracion = 0
        self.estado = "Abierto"
        self.profit = 0
        self.stop = stop
        self.precio_minimo_anterior = precio_minimo_anterior

    def analizar(self, row):
        if self.precio_venta <= row["high"]:
            self.estado = "Cerrado"
            self.monto_venta = self.cantidad * self.precio_venta
            self.profit = self.monto_compra + (self.monto_venta - self.monto_compra)
        elif row["close"] <= self.precio_stop:
            self.estado = "Stop"
            self.precio_venta = self.precio_stop
            self.monto_venta = self.cantidad * self.precio_stop
            self.profit = self.monto_compra + (self.monto_venta - self.monto_compra)
        else:
            self.duracion += 1
        return self.profit, self.estado

    def abierto(self):
        if self.estado == "Abierto":
            return True
        else:
            return False

    def info(self):
        print(
            "Precio compra: ",
            self.precio_entrada,
            " Monto: ",
            self.monto_compra,
            " | Precio_venta: ",
            self.precio_venta,
            " Profit: ",
            self.profit,
            " Monto: ",
            self.monto_venta,
            " | Duración: ",
            self.duracion,
            " | Estado: ",
            self.estado,
        )


class Trade_dos:
    precio_entrada = 0
    precio_venta = 0
    cantidad = 0
    monto_compra = 0
    monto_venta = 0
    duracion = 0  # cuantas velas demoró en cerrarse
    estado = "Abierto"  # Abierto, Cerrado, Stop
    profit = 0  # Beneficio en dolares

    def __init__(self, precio, monto_compra, profit):
        self.precio_entrada = precio
        self.monto_compra = monto_compra
        self.cantidad = monto_compra / precio
        self.precio_venta = precio * profit
        self.duracion = 0
        self.estado = "Abierto"
        self.profit = 0

    def analizar(self, row):
        if self.precio_venta <= row["close"]:
            self.estado = "Cerrado"
            self.monto_venta = self.cantidad * self.precio_venta
            self.profit = self.monto_venta
        else:
            self.duracion += 1
        return self.profit, self.estado

    def abierto(self):
        if self.estado == "Abierto":
            return True
        else:
            return False

    def info(self):
        print(
            "Precio compra: ",
            self.precio_entrada,
            " Monto: ",
            self.monto_compra,
            " | Precio_venta: ",
            self.precio_venta,
            " Profit: ",
            self.profit,
            " Monto: ",
            self.monto_venta,
            " | Duración: ",
            self.duracion,
            " | Estado: ",
            self.estado,
        )


class Reverse_ratio_0_5:
    capital = 1000.00
    profit = 1.01
    loss = 0.98
    monto_trade = 0.1
    posicionado = False
    max_n_trades = 0
    n_trades = 0
    min_distancia = 10
    distancia = 0
    buys = []
    lista_buys = []
    lista_sells = []
    lista_fondos = []
    lista_periodos = []
    lista_invertido = []
    wins = 0
    perdidas = 0

    def __init__(
        self, capital=1000, profit=1.01, loss=0.98, monto_trade=0.25, min_distancia=12
    ):
        self.capital = capital
        self.profit = profit
        self.loss = loss
        self.n_trades = 0
        self.max_n_trades = capital / (capital * monto_trade)
        self.monto_trade = capital * monto_trade
        self.min_distancia = min_distancia
        self.distancia = 0
        self.buys = []
        self.lista_buys = []
        self.lista_sells = []
        self.lista_fondos = []
        self.lista_periodos = []
        self.lista_invertido = []

    def procesarDataset(self, dataset):
        for index, row in dataset.iterrows():
            comprado = False
            vendido = False
            capital_invertido = 0
            for tr in self.buys:
                if tr.abierto():
                    resultado, estado = tr.analizar(row)
                    if estado == "Cerrado":
                        self.wins += 1
                    if estado == "Stop":
                        self.perdidas += 1
                    if estado != "Abierto":
                        self.n_trades -= 1
                        vendido = True
                        self.lista_periodos.append(len(self.buys))
                        self.capital += resultado*0.9985
                    else:
                        capital_invertido += tr.cantidad * row["close"]
            if row["predicted"]:
                if (
                    self.n_trades < self.max_n_trades
                    and self.distancia >= self.min_distancia
                ):
                    trade_buy = Trade(
                        row["close"],
                        self.capital / (self.max_n_trades - self.n_trades),
                        self.profit,
                        self.loss,
                        row["prev"]
                    )
                    self.buys.append(trade_buy)
                    capital_invertido += self.capital / (
                        self.max_n_trades - self.n_trades
                    )
                    self.capital -= self.capital / (self.max_n_trades - self.n_trades)
                    self.n_trades += 1
                    self.distancia = 0
                    comprado = True

            self.distancia += 1
            self.lista_buys.append(comprado)
            self.lista_sells.append(vendido)
            self.lista_fondos.append(self.capital + capital_invertido)
            self.lista_invertido.append(capital_invertido)


class Promedio_creciente:
    capital = 1000.00
    profit = 1.01
    loss = 0.98
    precio_compra_promedio = 0
    divisor_inicial = 20
    maxima_n_compras = 12
    periodo = 0
    cantidad_total = 0
    monto_total = 0
    posicionado = False
    min_distancia = 1
    distancia = 0
    lista_periodos = []
    lista_buys = []
    lista_sells = []
    lista_fondos = []
    wins = 0
    perdidas = 0
    capital_invertido = 0

    def __init__(
        self,
        capital=1000,
        max_compras=15,
        divisor_inicial=25,
        profit=1.01,
        min_distancia=10,
    ):
        self.capital = capital
        self.maxima_n_compras = max_compras
        self.divisor_inicial = divisor_inicial
        self.profit = profit
        self.min_distancia = int(min_distancia)
        self.distancia = int(min_distancia)
        self.lista_periodos = []
        self.lista_buys = []
        self.lista_sells = []
        self.lista_fondos = []
        self.lista_invertido = []

    def promediarPrecioCompra(self, promedio, precio, cantidad, total_cantidad):
        return (promedio * total_cantidad + precio * cantidad) / (
            cantidad + total_cantidad
        )

    def obtenerDivisor(self, inicial, indice, periodo):
        return inicial * (1 - (indice * periodo))

    def procesarDataset(self, dataset):
        for index, row in dataset.iterrows():
            if row["predicted"]:
                self.lista_sells.append(False)
                if (
                    self.periodo < self.maxima_n_compras
                    and self.distancia >= self.min_distancia
                ):
                    precio_compra = row["close"]
                    divisor = self.obtenerDivisor(
                        self.divisor_inicial, 1 / self.maxima_n_compras, self.periodo
                    )
                    self.periodo += 1
                    monto_entrada = self.capital / divisor
                    cantidad_compra = (monto_entrada*0.999) / precio_compra
                    self.precio_compra_promedio = self.promediarPrecioCompra(
                        self.precio_compra_promedio,
                        precio_compra,
                        cantidad_compra,
                        self.cantidad_total,
                    )
                    self.capital -= monto_entrada
                    self.cantidad_total += cantidad_compra
                    self.capital_invertido = self.cantidad_total * row["close"]
                    self.monto_total += monto_entrada
                    self.posicionado = True
                    self.lista_buys.append(True)
                    self.distancia = 0
                    # print("COMPRA -- Capital: ",self.capital, " Periodo: ",self.periodo," Promedio: ",self.precio_compra_promedio," Precio: ", precio_compra, " Monto: ",monto_entrada, ' Divisor: ',divisor)
                else:
                    self.distancia += 1
                    self.lista_buys.append(False)
                    self.capital_invertido = self.cantidad_total * row["close"]
            else:
                self.distancia += 1
                self.lista_buys.append(False)
                if self.posicionado:
                    if row["high"] >= self.precio_compra_promedio * self.profit:
                        monto_salida = (
                            self.precio_compra_promedio
                            * self.profit
                            * self.cantidad_total
                        )
                        self.capital += (monto_salida*0.999)
                        self.lista_periodos.append(self.periodo)
                        # print("VENTA -- Capital: ",self.capital, " Periodo: ",self.periodo," Promedio: ",self.precio_compra_promedio," Precio: ", row['Close']," Monto: ",monto_salida)
                        self.periodo = 0
                        self.precio_compra_promedio = 0
                        self.capital_invertido = 0
                        self.posicionado = False
                        self.cantidad_total = 0
                        self.monto_total = 0
                        self.lista_sells.append(True)
                        self.distancia = self.min_distancia
                    else:
                        self.lista_sells.append(False)
                        self.capital_invertido = self.cantidad_total * row["close"]
                else:
                    self.lista_sells.append(False)
            self.lista_fondos.append(self.capital_invertido + self.capital)
            self.lista_invertido.append(self.capital_invertido)


class Promedio_creciente_stop:
    capital = 1000.00
    profit = 1.01
    loss = 0.98
    precio_compra_promedio = 0
    divisor_inicial = 20
    maxima_n_compras = 12
    periodo = 0
    cantidad_total = 0
    monto_total = 0
    posicionado = False
    min_distancia = 1
    distancia = 0
    lista_periodos = []
    lista_buys = []
    lista_sells = []
    lista_fondos = []
    wins = 0
    perdidas = 0
    capital_invertido = 0

    def __init__(
        self,
        capital=1000,
        max_compras=15,
        divisor_inicial=25,
        profit=1.01,
        min_distancia=10,
    ):
        self.capital = capital
        self.maxima_n_compras = max_compras
        self.divisor_inicial = divisor_inicial
        self.profit = profit
        self.min_distancia = min_distancia
        self.distancia = min_distancia
        self.lista_periodos = []
        self.lista_buys = []
        self.lista_sells = []
        self.lista_fondos = []
        self.lista_invertido = []

    def promediarPrecioCompra(self, promedio, precio, cantidad, total_cantidad):
        return (promedio * total_cantidad + precio * cantidad) / (
            cantidad + total_cantidad
        )

    def obtenerDivisor(self, inicial, indice, periodo):
        return inicial * (1 - (indice * periodo))

    def procesarDataset(self, dataset):
        for index, row in dataset.iterrows():
            if row["predicted"]:
                self.lista_sells.append(False)
                if (
                    self.periodo < self.maxima_n_compras
                    and self.distancia >= self.min_distancia
                ):
                    precio_compra = row["close"]
                    divisor = self.obtenerDivisor(
                        self.divisor_inicial, 1 / self.maxima_n_compras, self.periodo
                    )
                    self.periodo += 1
                    monto_entrada = self.capital / divisor
                    cantidad_compra = monto_entrada / precio_compra
                    self.precio_compra_promedio = self.promediarPrecioCompra(
                        self.precio_compra_promedio,
                        precio_compra,
                        cantidad_compra,
                        self.cantidad_total,
                    )
                    self.capital -= monto_entrada
                    self.cantidad_total += cantidad_compra
                    self.capital_invertido = self.cantidad_total * row["close"]
                    self.monto_total += monto_entrada
                    self.posicionado = True
                    self.lista_buys.append(True)
                    self.distancia = 0
                    # print("COMPRA -- Capital: ",self.capital, " Periodo: ",self.periodo," Promedio: ",self.precio_compra_promedio," Precio: ", precio_compra, " Monto: ",monto_entrada, ' Divisor: ',divisor)
                else:
                    self.distancia += 1
                    self.lista_buys.append(False)
                    self.capital_invertido = self.cantidad_total * row["close"]
            else:
                self.distancia += 1
                self.lista_buys.append(False)
                if self.posicionado:
                    if row["high"] >= self.precio_compra_promedio * self.profit:
                        monto_salida = (
                            self.precio_compra_promedio
                            * self.profit
                            * self.cantidad_total
                        )
                        self.capital += monto_salida
                        self.lista_periodos.append(self.periodo)
                        # print("VENTA -- Capital: ",self.capital, " Periodo: ",self.periodo," Promedio: ",self.precio_compra_promedio," Precio: ", row['Close']," Monto: ",monto_salida)
                        self.periodo = 0
                        self.precio_compra_promedio = 0
                        self.capital_invertido = 0
                        self.posicionado = False
                        self.cantidad_total = 0
                        self.monto_total = 0
                        self.lista_sells.append(True)
                        self.distancia = self.min_distancia
                    else:
                        self.lista_sells.append(False)
                        self.capital_invertido = self.cantidad_total * row["close"]
                else:
                    self.lista_sells.append(False)
            self.lista_fondos.append(self.capital_invertido + self.capital)
            self.lista_invertido.append(self.capital_invertido)


class Promedio_creciente_tres:
    capital = 1000.00
    profit = 1.01
    loss = 0.98
    precio_compra_promedio = 0
    divisor_inicial = 20
    maxima_n_compras = 12
    periodo = 0
    cantidad_total = 0
    monto_total = 0
    posicionado = False
    min_distancia = 1
    distancia = 0
    lista_periodos = []
    lista_buys = []
    lista_sells = []
    lista_fondos = []
    buys = []
    wins = 0
    perdidas = 0
    capital_invertido = 0

    def __init__(
        self,
        capital=1000,
        max_compras=15,
        divisor_inicial=25,
        profit=1.01,
        min_distancia=10,
    ):
        self.capital = capital
        self.maxima_n_compras = max_compras
        self.divisor_inicial = divisor_inicial
        self.profit = profit
        self.min_distancia = min_distancia
        self.distancia = min_distancia
        self.lista_periodos = []
        self.lista_buys = []
        self.lista_sells = []
        self.lista_fondos = []
        self.lista_invertido = []

    def promediarPrecioCompra(self, promedio, precio, cantidad, total_cantidad):
        return (promedio * total_cantidad + precio * cantidad) / (
            cantidad + total_cantidad
        )

    def obtenerDivisor(self, inicial, indice, periodo):
        return inicial * (1 - (indice * periodo))

    def procesarDataset(self, dataset):
        for index, row in dataset.iterrows():
            self.cantidad_total = 0
            flag_vendido = False
            if len(self.buys) > 0:
                for index2, tr in enumerate(self.buys):
                    if tr.abierto():
                        resultado, estado = tr.analizar(row)
                        if estado == "Cerrado":
                            self.wins += 1
                            self.periodo -= 1
                            self.capital += resultado
                            self.monto_total -= tr.monto_compra
                            flag_vendido = True
                            print("cantidad total: ", self.cantidad_total)
                            print("periodo: ", self.periodo)
                            print(len(self.buys))
                            del self.buys[index2]
                            print(len(self.buys))
                            print("vendido")
                        else:
                            self.cantidad_total += tr.cantidad
                    if len(self.buys) > 0:
                        self.posicionado = True
                    else:
                        self.posicionado = False
            if row["predicted"]:
                self.lista_sells.append(False)
                if (
                    self.periodo < self.maxima_n_compras
                    and self.distancia >= self.min_distancia
                ):
                    print("comprado")
                    precio_compra = row["close"]
                    divisor = self.obtenerDivisor(
                        self.divisor_inicial, 1 / self.maxima_n_compras, self.periodo
                    )
                    self.periodo += 1
                    monto_entrada = self.capital / divisor
                    trade_buy = Trade_dos(row["close"], monto_entrada, self.profit)
                    self.buys.append(trade_buy)
                    self.capital -= monto_entrada
                    self.monto_total += monto_entrada
                    self.posicionado = True
                    self.lista_buys.append(True)
                    self.distancia = 0
                    # print("COMPRA -- Capital: ",self.capital, " Periodo: ",self.periodo," Promedio: ",self.precio_compra_promedio," Precio: ", precio_compra, " Monto: ",monto_entrada, ' Divisor: ',divisor)
                else:
                    self.distancia += 1
                    self.lista_buys.append(False)
            else:
                self.distancia += 1
                self.lista_buys.append(False)
                if flag_vendido:
                    self.lista_periodos.append(self.periodo)
                    self.lista_sells.append(True)
                    self.distancia = self.min_distancia
                else:
                    self.lista_sells.append(False)
            self.lista_fondos.append(
                (self.cantidad_total * row["close"]) + self.capital
            )
            self.lista_invertido.append(self.cantidad_total * row["close"])


class Promedio_creciente_dos:
    capital = 1000.00
    profit = 1.01
    loss = 0.98
    precio_compra_promedio = 0
    divisor_inicial = 20
    maxima_n_compras = 12
    periodo = 0
    cantidad_total = 0
    monto_total = 0
    posicionado = False
    min_distancia = 1
    distancia = 0
    lista_periodos = []
    lista_buys = []
    lista_sells = []
    lista_fondos = []
    wins = 0
    perdidas = 0
    capital_invertido = 0

    def __init__(
        self,
        capital=1000,
        max_compras=15,
        divisor_inicial=25,
        profit=1.01,
        min_distancia=10,
    ):
        self.capital = capital
        self.maxima_n_compras = max_compras
        self.divisor_inicial = divisor_inicial
        self.profit = profit
        self.min_distancia = min_distancia
        self.distancia = min_distancia
        self.lista_periodos = []
        self.lista_buys = []
        self.lista_sells = []
        self.lista_fondos = []
        self.lista_invertido = []

    def promediarPrecioCompra(self, promedio, precio, cantidad, total_cantidad):
        return (promedio * total_cantidad + precio * cantidad) / (
            cantidad + total_cantidad
        )

    def obtenerDivisor(self, inicial, indice, periodo):
        return inicial * (1 - (indice * periodo))

    def procesarDataset(self, dataset):
        for index, row in dataset.iterrows():
            if row["predicted"]:
                self.lista_sells.append(False)
                if (
                    self.periodo < self.maxima_n_compras
                    and self.distancia >= self.min_distancia
                ):
                    precio_compra = row["close"]
                    divisor = self.obtenerDivisor(
                        self.divisor_inicial, 1 / self.maxima_n_compras, self.periodo
                    )
                    self.periodo += 1
                    monto_entrada = self.capital / divisor
                    cantidad_compra = monto_entrada / precio_compra
                    self.precio_compra_promedio = self.promediarPrecioCompra(
                        self.precio_compra_promedio,
                        precio_compra,
                        cantidad_compra,
                        self.cantidad_total,
                    )
                    self.capital -= monto_entrada
                    self.cantidad_total += cantidad_compra
                    self.capital_invertido = self.cantidad_total * row["close"]
                    self.monto_total += monto_entrada
                    self.posicionado = True
                    self.lista_buys.append(True)
                    self.distancia = 0
                    # print("COMPRA -- Capital: ",self.capital, " Periodo: ",self.periodo," Promedio: ",self.precio_compra_promedio," Precio: ", precio_compra, " Monto: ",monto_entrada, ' Divisor: ',divisor)
                else:
                    self.distancia += 1
                    self.lista_buys.append(False)
                    self.capital_invertido = self.cantidad_total * row["close"]
            else:
                self.distancia += 1
                self.lista_buys.append(False)
                if self.posicionado:
                    if self.periodo > 1:
                        if row["high"] >= self.precio_compra_promedio:
                            monto_salida = (
                                self.precio_compra_promedio * self.cantidad_total
                            )
                            self.capital += monto_salida
                            self.lista_periodos.append(self.periodo)
                            # print("VENTA -- Capital: ",self.capital, " Periodo: ",self.periodo," Promedio: ",self.precio_compra_promedio," Precio: ", row['Close']," Monto: ",monto_salida)
                            self.periodo = 0
                            self.precio_compra_promedio = 0
                            self.capital_invertido = 0
                            self.posicionado = False
                            self.cantidad_total = 0
                            self.monto_total = 0
                            self.lista_sells.append(True)
                            self.distancia = self.min_distancia
                        else:
                            self.lista_sells.append(False)
                            self.capital_invertido = self.cantidad_total * row["close"]
                    else:
                        if row["high"] >= self.precio_compra_promedio * self.profit:
                            monto_salida = (
                                self.precio_compra_promedio
                                * self.profit
                                * self.cantidad_total
                            )
                            self.capital += monto_salida
                            self.lista_periodos.append(self.periodo)
                            # print("VENTA -- Capital: ",self.capital, " Periodo: ",self.periodo," Promedio: ",self.precio_compra_promedio," Precio: ", row['Close']," Monto: ",monto_salida)
                            self.periodo = 0
                            self.precio_compra_promedio = 0
                            self.capital_invertido = 0
                            self.posicionado = False
                            self.cantidad_total = 0
                            self.monto_total = 0
                            self.lista_sells.append(True)
                            self.distancia = self.min_distancia
                        else:
                            self.lista_sells.append(False)
                            self.capital_invertido = self.cantidad_total * row["close"]
                else:
                    self.lista_sells.append(False)
            self.lista_fondos.append(self.capital_invertido + self.capital)
            self.lista_invertido.append(self.capital_invertido)


class Estrategia_dca:
    capital = 10000.00
    precio_compra_promedio = 0
    maxima_n_compras = 100
    periodo = 0
    monto_x_compra = 0
    cantidad_total = 0
    monto_total = 0
    min_distancia = 1
    distancia = 0
    lista_buys = []
    lista_promedio = []
    lista_fondos = []

    def __init__(self, capital=10000, max_compras=100, min_distancia=10):
        self.capital = capital
        self.maxima_n_compras = max_compras
        self.min_distancia = min_distancia
        self.distancia = min_distancia
        self.monto_x_compra = capital / self.maxima_n_compras
        self.lista_buys = []
        self.lista_promedio = []
        self.lista_fondos = []

    def promediarPrecioCompra(self, promedio, precio, cantidad, total_cantidad):
        return (promedio * total_cantidad + precio * cantidad) / (
            cantidad + total_cantidad
        )

    def procesarDataset_rf(self, dataset):
        for index, row in dataset.iterrows():
            if row["predicted"]:
                if (
                    self.periodo < self.maxima_n_compras
                    and self.distancia >= self.min_distancia
                ):
                    precio_compra = row["close"]
                    self.periodo += 1
                    monto_entrada = self.monto_x_compra
                    cantidad_compra = monto_entrada / precio_compra
                    self.precio_compra_promedio = self.promediarPrecioCompra(
                        self.precio_compra_promedio,
                        precio_compra,
                        cantidad_compra,
                        self.cantidad_total,
                    )
                    self.capital -= monto_entrada
                    self.cantidad_total += cantidad_compra
                    self.monto_total += monto_entrada
                    self.lista_buys.append(True)
                    self.distancia = 0
                    # print("COMPRA -- Capital: ",self.capital, " Periodo: ",self.periodo," Promedio: ",self.precio_compra_promedio," Precio: ", precio_compra, " Monto: ",monto_entrada)
                else:
                    self.distancia += 1
                    self.lista_buys.append(False)
            else:
                self.distancia += 1
                self.lista_buys.append(False)
            self.lista_promedio.append(self.precio_compra_promedio)
            self.lista_fondos.append(
                self.capital + (self.cantidad_total * row["close"])
            )

    def procesarDataset(self, dataset, nvelas):
        aux = nvelas
        for index, row in dataset.iterrows():
            if aux == nvelas:
                if (
                    self.periodo < self.maxima_n_compras
                    and self.distancia >= self.min_distancia
                ):
                    aux = 0
                    precio_compra = row["close"]
                    self.periodo += 1
                    monto_entrada = self.monto_x_compra
                    cantidad_compra = monto_entrada / precio_compra
                    self.precio_compra_promedio = self.promediarPrecioCompra(
                        self.precio_compra_promedio,
                        precio_compra,
                        cantidad_compra,
                        self.cantidad_total,
                    )
                    self.capital -= monto_entrada
                    self.cantidad_total += cantidad_compra
                    self.monto_total += monto_entrada
                    self.lista_buys.append(True)
                    self.distancia = 0
                    # print("COMPRA -- Capital: ",self.capital, " Periodo: ",self.periodo," Promedio: ",self.precio_compra_promedio," Precio: ", precio_compra, " Monto: ",monto_entrada)
                else:
                    self.distancia += 1
                    self.lista_buys.append(False)
            else:
                aux += 1
                self.distancia += 1
                self.lista_buys.append(False)
            self.lista_promedio.append(self.precio_compra_promedio)
            self.lista_fondos.append(
                self.capital + (self.cantidad_total * row["close"])
            )

