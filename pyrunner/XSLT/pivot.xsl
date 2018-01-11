<?xml version="1.0" encoding="UTF-8" ?>
<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    version="1.0">
    <xsl:output type="html" encoding="UTF-8" indent="yes" />

    <xsl:template match="/">
        <html>
            <body>
                <table>
                    <tr>
                        <th>Benchmark</th>
                        <th>Testcase</th>
                        <th>Command</th>
                        <th>Time</th>
                        <th>Memory</th>
                        <th>Validator</th>
                        <th>Time valid</th>
                        <th>Memory valid</th>
                    </tr>
                    <xsl:apply-templates select="pyrunner/benchmark/testcase/command" />
                </table>
            </body>
        </html>
    </xsl:template>
    
    <xsl:template match="command">
        <tr>
            <td><xsl:value-of select="ancestor::benchmark[1]/@id" /></td>
            <td><xsl:value-of select="ancestor::testcase[1]/@id" /></td>
            <td><xsl:value-of select="@id" /></td>
            <xsl:apply-templates select="*" modes="TableData" />
        </tr>
    </xsl:template>
    
    <xsl:template match="command/pyrunlim" modes="TableData">
        <td><xsl:value-of select="format-number(stats/@time, '0.00')" /></td>
        <td><xsl:value-of select="format-number(stats/@memory, '0.0')" /></td>
        <td><xsl:value-of select="../validator/@response" /></td>
        <xsl:choose>
            <xsl:when test="stats/@status = 'complete' and ../validator/@response = 'yes'">
                <td><xsl:value-of select="format-number(stats/@time, '0.00')" /></td>
                <td><xsl:value-of select="format-number(stats/@memory, '0.0')" /></td>
            </xsl:when>
            <xsl:otherwise>
                <td>n/a</td>
                <td>n/a</td>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="command/skip" modes="TableData">
    </xsl:template>
</xsl:stylesheet>
