def parse_csv_line(line):
    fields, i, n = [], 0, len(line)
    while True:
        if i < n and line[i] == '"':
            i += 1
            buf = []
            while True:
                if i >= n:
                    raise ValueError("unterminated quote")
                if line[i] == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        buf.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                buf.append(line[i])
                i += 1
            fields.append("".join(buf))
            if i == n:
                return fields
            if line[i] != ",":
                raise ValueError("text after closing quote")
            i += 1
        else:
            j = line.find(",", i)
            if j < 0:
                fields.append(line[i:])
                return fields
            fields.append(line[i:j])
            i = j + 1
